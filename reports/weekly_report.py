"""
每周报告生成器

生成每周趋势报告并推送到Telegram
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json

from database.db_manager import DatabaseManager
from scorers.scorer import categorize_repo, CATEGORIES
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WeeklyReport:
    report_date: str
    period_start: str
    period_end: str
    total_repos: int
    new_repos: int
    analyzed_repos: int
    high_score_repos: int
    top_gainers: List[Dict[str, Any]] = field(default_factory=list)
    top_by_score: List[Dict[str, Any]] = field(default_factory=list)
    by_category: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    by_source: Dict[str, int] = field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


class WeeklyReportGenerator:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()
    
    def generate(self, days: int = 7) -> WeeklyReport:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        report = WeeklyReport(
            report_date=end_date.strftime("%Y-%m-%d"),
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
            total_repos=0,
            new_repos=0,
            analyzed_repos=0,
            high_score_repos=0
        )
        
        report.total_repos = self.db.get_total_repositories()
        report.new_repos = self._count_new_repos(start_date)
        report.analyzed_repos = self.db.get_total_analyzed_repositories()
        report.high_score_repos = self._count_high_score_repos(70)
        
        report.top_gainers = self._get_top_gainers(start_date, limit=10)
        report.top_by_score = self._get_top_scored(limit=10)
        report.by_category = self._get_top_by_category(limit=5)
        report.by_source = self._get_source_distribution()
        report.recommendations = self._get_recommendations(limit=5)
        
        logger.info(f"Generated weekly report: {report.total_repos} repos, {report.new_repos} new")
        
        return report
    
    def _count_new_repos(self, since: datetime) -> int:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM repositories 
                WHERE first_seen_at >= ?
            ''', (since.isoformat(),))
            return cursor.fetchone()[0]
    
    def _count_high_score_repos(self, min_score: float) -> int:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM scores 
                WHERE total_score >= ?
            ''', (min_score,))
            return cursor.fetchone()[0]
    
    def _get_top_gainers(self, since: datetime, limit: int = 10) -> List[Dict]:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.id, r.name, r.full_name, r.stars, r.html_url, r.source,
                       s.total_score
                FROM repositories r
                LEFT JOIN scores s ON r.id = s.repo_id
                WHERE r.first_seen_at >= ?
                ORDER BY r.stars DESC
                LIMIT ?
            ''', (since.isoformat(), limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def _get_top_scored(self, limit: int = 10) -> List[Dict]:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.id, r.name, r.full_name, r.stars, r.html_url, r.source,
                       s.total_score, s.score_popularity, s.score_growth
                FROM repositories r
                JOIN scores s ON r.id = s.repo_id
                ORDER BY s.total_score DESC
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def _get_top_by_category(self, limit: int = 5) -> Dict[str, List[Dict]]:
        result = {}
        
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.id, r.name, r.full_name, r.stars, r.html_url, r.topics, r.source,
                       s.total_score
                FROM repositories r
                JOIN scores s ON r.id = s.repo_id
                ORDER BY s.total_score DESC
            ''')
            
            repos = cursor.fetchall()
            
            categorized = {cat: [] for cat in CATEGORIES.keys()}
            
            for row in repos:
                repo = dict(row)
                topics = json.loads(repo.get('topics', '[]')) if repo.get('topics') else []
                category = categorize_repo(topics)
                
                if len(categorized[category]) < limit:
                    categorized[category].append(repo)
            
            result = {k: v for k, v in categorized.items() if v}
        
        return result
    
    def _get_source_distribution(self) -> Dict[str, int]:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT source, COUNT(*) as count 
                FROM repositories 
                GROUP BY source
            ''')
            
            return {row['source']: row['count'] for row in cursor.fetchall()}
    
    def _get_recommendations(self, limit: int = 5) -> List[Dict]:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.id, r.name, r.full_name, r.description, r.stars, r.html_url,
                       a.monetization_potential, a.differentiation_ideas,
                       s.total_score
                FROM repositories r
                JOIN scores s ON r.id = s.repo_id
                LEFT JOIN analysis_results a ON r.id = a.repo_id
                WHERE s.total_score >= 70
                ORDER BY s.total_score DESC
                LIMIT ?
            ''', (limit,))
            
            recommendations = []
            for row in cursor.fetchall():
                repo = dict(row)
                ideas = repo.get('differentiation_ideas', '[]')
                if isinstance(ideas, str):
                    try:
                        repo['differentiation_ideas'] = json.loads(ideas)
                    except:
                        repo['differentiation_ideas'] = []
                recommendations.append(repo)
            
            return recommendations
    
    def format_telegram_message(self, report: WeeklyReport) -> str:
        lines = [
            "📊 <b>GitHub Radar 周报</b>",
            f"📅 {report.period_start} ~ {report.period_end}",
            "",
            f"📈 <b>本周数据</b>",
            f"• 总项目: {report.total_repos}",
            f"• 新增: {report.new_repos}",
            f"• 已分析: {report.analyzed_repos}",
            f"• 高分项目: {report.high_score_repos}",
            "",
        ]
        
        if report.by_source:
            lines.append("📡 <b>数据来源</b>")
            for source, count in report.by_source.items():
                lines.append(f"• {source}: {count}")
            lines.append("")
        
        if report.top_by_score:
            lines.append("🏆 <b>Top 5 高分项目</b>")
            for i, repo in enumerate(report.top_by_score[:5], 1):
                score = repo.get('total_score', 0)
                lines.append(f"{i}. {repo['name']} ({score:.1f}分)")
            lines.append("")
        
        if report.by_category:
            lines.append("📂 <b>各领域热门</b>")
            for category, repos in list(report.by_category.items())[:3]:
                if repos:
                    lines.append(f"\n<b>{category}</b>")
                    for repo in repos[:3]:
                        lines.append(f"• {repo['name']}")
            lines.append("")
        
        if report.recommendations:
            lines.append("💡 <b>本周推荐</b>")
            for repo in report.recommendations[:3]:
                lines.append(f"\n<b>{repo['name']}</b>")
                lines.append(f"评分: {repo.get('total_score', 0):.1f}")
                if repo.get('monetization_potential'):
                    lines.append(f"变现: {repo['monetization_potential'][:50]}...")
        
        lines.append("")
        lines.append("🔗 查看详情: Dashboard")
        
        return "\n".join(lines)
    
    def format_markdown_report(self, report: WeeklyReport) -> str:
        lines = [
            f"# GitHub Radar 周报",
            f"",
            f"**报告周期**: {report.period_start} ~ {report.period_end}",
            f"",
            f"## 📈 数据概览",
            f"",
            f"| 指标 | 数量 |",
            f"|------|------|",
            f"| 总项目 | {report.total_repos} |",
            f"| 本周新增 | {report.new_repos} |",
            f"| 已分析 | {report.analyzed_repos} |",
            f"| 高分项目 (≥70) | {report.high_score_repos} |",
            f"",
        ]
        
        if report.by_source:
            lines.append("## 📡 数据来源")
            lines.append("")
            lines.append("| 来源 | 数量 |")
            lines.append("|------|------|")
            for source, count in report.by_source.items():
                lines.append(f"| {source} | {count} |")
            lines.append("")
        
        if report.top_by_score:
            lines.append("## 🏆 高分项目 Top 10")
            lines.append("")
            lines.append("| 排名 | 项目 | Stars | 评分 |")
            lines.append("|------|------|-------|------|")
            for i, repo in enumerate(report.top_by_score, 1):
                lines.append(f"| {i} | [{repo['name']}]({repo['html_url']}) | {repo.get('stars', 0)} | {repo.get('total_score', 0):.1f} |")
            lines.append("")
        
        if report.by_category:
            lines.append("## 📂 各领域热门")
            lines.append("")
            for category, repos in report.by_category.items():
                if repos:
                    lines.append(f"### {category}")
                    lines.append("")
                    for repo in repos:
                        lines.append(f"- [{repo['name']}]({repo['html_url']}) - {repo.get('total_score', 0):.1f}分")
                    lines.append("")
        
        if report.recommendations:
            lines.append("## 💡 本周推荐")
            lines.append("")
            for repo in report.recommendations:
                lines.append(f"### [{repo['name']}]({repo['html_url']})")
                lines.append("")
                lines.append(f"**评分**: {repo.get('total_score', 0):.1f}")
                lines.append("")
                if repo.get('description'):
                    lines.append(f"**描述**: {repo['description']}")
                    lines.append("")
                if repo.get('monetization_potential'):
                    lines.append(f"**变现场景**: {repo['monetization_potential']}")
                    lines.append("")
                ideas = repo.get('differentiation_ideas', [])
                if ideas:
                    lines.append("**差异化方向**:")
                    for idea in ideas[:3]:
                        lines.append(f"- {idea}")
                    lines.append("")
        
        lines.append("---")
        lines.append(f"*生成时间: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(lines)


def send_weekly_report():
    generator = WeeklyReportGenerator()
    report = generator.generate(days=7)
    
    telegram_message = generator.format_telegram_message(report)
    
    markdown_report = generator.format_markdown_report(report)
    
    report_path = f"weekly_report_{report.report_date}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)
    
    logger.info(f"Weekly report saved to {report_path}")
    
    from notifiers.telegram_notifier import TelegramNotifier
    from config import config
    
    notifier = TelegramNotifier(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id
    )
    
    notifier.send_message(telegram_message)
    
    return report


if __name__ == "__main__":
    report = send_weekly_report()
    print(f"Report generated: {report.report_date}")
