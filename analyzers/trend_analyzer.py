import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import Counter

from database.db_manager import DatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)


class TrendAnalyzer:
    CATEGORY_KEYWORDS = {
        'AI/LLM': ['ai', 'llm', 'gpt', 'claude', 'gemini', 'openai', 'anthropic',
                     'chatbot', 'language-model', 'transformer', 'diffusion', 'stable-diffusion',
                     'deepseek', 'llama', 'mistral', 'rag', 'embedding', 'vector',
                     'neural', 'machine-learning', 'deep-learning', 'ml'],
        'Agent/自动化': ['agent', 'automation', 'workflow', 'orchestrat', 'autonomous',
                        'mcp', 'tool-use', 'function-call', 'copilot', 'cursor'],
        'Web开发': ['react', 'vue', 'svelte', 'nextjs', 'next.js', 'nuxt', 'angular',
                    'tailwind', 'frontend', 'fullstack', 'web-app', 'spa'],
        'DevOps/云原生': ['kubernetes', 'docker', 'terraform', 'k8s', 'helm', 'ci-cd',
                          'devops', 'cloud-native', 'microservice', 'serverless'],
        '数据库/存储': ['database', 'sql', 'nosql', 'redis', 'postgres', 'mongodb',
                       'vector-db', 'search-engine', 'storage'],
        '安全/隐私': ['security', 'privacy', 'encryption', 'vpn', 'firewall', 'CVE',
                      'vulnerability', 'zero-day', 'pentest'],
        '移动端': ['ios', 'android', 'swift', 'kotlin', 'flutter', 'react-native',
                   'mobile', 'app'],
        '区块链/Web3': ['blockchain', 'crypto', 'defi', 'nft', 'solana', 'ethereum',
                        'web3', 'smart-contract'],
        'Rust/系统编程': ['rust', 'zig', 'wasm', 'webassembly', 'system-programming'],
        '开发工具': ['cli', 'terminal', 'editor', 'ide', 'debugger', 'linter',
                    'formatter', 'dev-tools', 'developer-tools'],
    }
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def analyze_trends(self, days: int = 7) -> Dict:
        logger.info(f"Analyzing trends for last {days} days...")
        
        categories = self._categorize_recent_projects(days)
        hot_languages = self._get_hot_languages(days)
        hot_topics = self._get_hot_topics(days)
        source_distribution = self._get_source_distribution(days)
        growth_leaders = self._get_growth_leaders(days)
        
        return {
            'categories': categories,
            'hot_languages': hot_languages,
            'hot_topics': hot_topics,
            'source_distribution': source_distribution,
            'growth_leaders': growth_leaders,
            'period_days': days,
            'analyzed_at': datetime.now().isoformat()
        }
    
    def _categorize_recent_projects(self, days: int) -> List[Dict]:
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT r.full_name, r.description, r.topics, r.language, r.stars, r.source,
                   s.total_score
            FROM repositories r
            LEFT JOIN scores s ON r.id = s.repo_id
            WHERE r.first_seen_at >= ?
            ORDER BY r.stars DESC
        ''', (since,))
        
        rows = cursor.fetchall()
        conn.close()
        
        category_stats = {}
        for cat_name in self.CATEGORY_KEYWORDS:
            category_stats[cat_name] = {
                'count': 0,
                'total_stars': 0,
                'avg_score': 0.0,
                'top_projects': [],
                'scores': []
            }
        
        for row in rows:
            text = f"{row['full_name']} {row['description'] or ''} {row['topics'] or ''}".lower()
            stars = row['stars'] or 0
            score = row['total_score'] or 0
            
            matched = False
            for cat_name, keywords in self.CATEGORY_KEYWORDS.items():
                if any(kw.lower() in text for kw in keywords):
                    stats = category_stats[cat_name]
                    stats['count'] += 1
                    stats['total_stars'] += stars
                    stats['scores'].append(score)
                    if len(stats['top_projects']) < 3:
                        stats['top_projects'].append({
                            'name': row['full_name'],
                            'stars': stars,
                            'score': score
                        })
                    matched = True
            
            if not matched:
                stats = category_stats.setdefault('其他', {
                    'count': 0, 'total_stars': 0, 'avg_score': 0.0,
                    'top_projects': [], 'scores': []
                })
                stats['count'] += 1
                stats['total_stars'] += stars
                stats['scores'].append(score)
                if len(stats['top_projects']) < 3:
                    stats['top_projects'].append({
                        'name': row['full_name'],
                        'stars': stars,
                        'score': score
                    })
        
        result = []
        for cat_name, stats in category_stats.items():
            if stats['count'] > 0:
                avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
                result.append({
                    'category': cat_name,
                    'count': stats['count'],
                    'total_stars': stats['total_stars'],
                    'avg_score': round(avg_score, 1),
                    'top_projects': stats['top_projects']
                })
        
        result.sort(key=lambda x: x['count'], reverse=True)
        return result
    
    def _get_hot_languages(self, days: int) -> List[Dict]:
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT language, COUNT(*) as cnt, SUM(stars) as total_stars
            FROM repositories
            WHERE first_seen_at >= ? AND language IS NOT NULL AND language != ''
            GROUP BY language
            ORDER BY cnt DESC
            LIMIT 10
        ''', (since,))
        
        result = []
        for row in cursor.fetchall():
            result.append({
                'language': row[0],
                'count': row[1],
                'total_stars': row[2] or 0
            })
        
        conn.close()
        return result
    
    def _get_hot_topics(self, days: int) -> List[Dict]:
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT topics FROM repositories
            WHERE first_seen_at >= ? AND topics IS NOT NULL AND topics != ''
        ''', (since,))
        
        topic_counter = Counter()
        for row in cursor.fetchall():
            topics_str = row[0]
            if topics_str:
                try:
                    import json
                    topics = json.loads(topics_str)
                    for t in topics:
                        topic_counter[t] += 1
                except:
                    for t in topics_str.split(','):
                        t = t.strip().strip('"[]')
                        if t:
                            topic_counter[t] += 1
        
        conn.close()
        
        result = []
        for topic, count in topic_counter.most_common(15):
            result.append({'topic': topic, 'count': count})
        
        return result
    
    def _get_source_distribution(self, days: int) -> List[Dict]:
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT source, COUNT(*) as cnt
            FROM repositories
            WHERE first_seen_at >= ?
            GROUP BY source
            ORDER BY cnt DESC
        ''', (since,))
        
        result = []
        for row in cursor.fetchall():
            result.append({
                'source': row[0] or 'unknown',
                'count': row[1]
            })
        
        conn.close()
        return result
    
    def _get_growth_leaders(self, days: int) -> List[Dict]:
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('''
            SELECT r.full_name, r.stars, r.html_url,
                   (SELECT COUNT(*) FROM star_snapshots ss 
                    WHERE ss.repo_id = r.id AND ss.snapshot_at >= ?) as snapshot_count
            FROM repositories r
            WHERE r.first_seen_at >= ?
            ORDER BY r.stars DESC
            LIMIT 10
        ''', (since, since))
        
        result = []
        for row in cursor.fetchall():
            result.append({
                'name': row[0],
                'stars': row[1],
                'url': row[2]
            })
        
        conn.close()
        return result
    
    def format_trend_report(self, analysis: Dict) -> str:
        lines = ["🔥 *GitHub 技术趋势周报*"]
        days = analysis.get('period_days', 7)
        lines.append(f"📅 近 {days} 天数据分析\n")
        
        categories = analysis.get('categories', [])
        if categories:
            lines.append("📊 *热门方向 TOP5*")
            for i, cat in enumerate(categories[:5], 1):
                count = cat['count']
                avg = cat['avg_score']
                lines.append(f"  {i}. *{cat['category']}* — {count}个项目 均分{avg:.0f}")
                for proj in cat.get('top_projects', [])[:2]:
                    lines.append(f"     ↳ {proj['name']} ⭐{proj['stars']}")
            lines.append("")
        
        languages = analysis.get('hot_languages', [])
        if languages:
            lines.append("💻 *热门语言 TOP5*")
            lang_str = " | ".join([f"{l['language']}({l['count']})" for l in languages[:5]])
            lines.append(f"  {lang_str}")
            lines.append("")
        
        topics = analysis.get('hot_topics', [])
        if topics:
            lines.append("🏷 *热门标签 TOP5*")
            topic_str = " | ".join([f"#{t['topic']}({t['count']})" for t in topics[:5]])
            lines.append(f"  {topic_str}")
            lines.append("")
        
        sources = analysis.get('source_distribution', [])
        if sources:
            lines.append("📡 *数据来源*")
            src_str = " | ".join([f"{s['source']}({s['count']})" for s in sources])
            lines.append(f"  {src_str}")
        
        lines.append(f"\n🕐 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        return "\n".join(lines)
