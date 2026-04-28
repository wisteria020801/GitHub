import requests
import time
import threading
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from config import TelegramConfig
from database.models import Repository, Score, AnalysisResult
from database.db_manager import DatabaseManager
from notifiers.telegram_notifier import TelegramNotifier
from analyzers.trend_analyzer import TrendAnalyzer
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CommandHandler:
    command: str
    description: str
    callback: Callable


class TelegramCommandBot:
    def __init__(self, config: TelegramConfig, db_manager: DatabaseManager):
        self.config = config
        self.db = db_manager
        self.notifier = TelegramNotifier(config)
        self.trend_analyzer = TrendAnalyzer(db_manager)
        self.api_base = f"https://api.telegram.org/bot{config.bot_token}"
        self.last_update_id = 0
        self.running = False
        self.thread = None
        self.commands = self._register_commands()
        # 设置Telegram命令菜单
        self._set_commands_menu()
    
    def _register_commands(self) -> Dict[str, CommandHandler]:
        return {
            'start': CommandHandler(
                command='/start',
                description='显示帮助信息',
                callback=self.handle_start
            ),
            'help': CommandHandler(
                command='/help',
                description='显示帮助信息',
                callback=self.handle_help
            ),
            'top': CommandHandler(
                command='/top',
                description='查看评分最高的项目',
                callback=self.handle_top
            ),
            'stars': CommandHandler(
                command='/stars',
                description='查看Star最多的项目',
                callback=self.handle_stars
            ),
            'forks': CommandHandler(
                command='/forks',
                description='查看Fork最多的项目',
                callback=self.handle_forks
            ),
            'new': CommandHandler(
                command='/new',
                description='查看最新创建的项目',
                callback=self.handle_new
            ),
            'today': CommandHandler(
                command='/today',
                description='查看今日发现的项目',
                callback=self.handle_today
            ),
            'trending': CommandHandler(
                command='/trending',
                description='查看增长最快的项目',
                callback=self.handle_trending
            ),
            'source': CommandHandler(
                command='/source',
                description='按来源查看项目 (github/hackernews/producthunt)',
                callback=self.handle_source
            ),
            'lang': CommandHandler(
                command='/lang',
                description='按语言查看项目',
                callback=self.handle_language
            ),
            'search': CommandHandler(
                command='/search',
                description='搜索项目 (如: /search ai)',
                callback=self.handle_search
            ),
            'stats': CommandHandler(
                command='/stats',
                description='查看系统统计信息',
                callback=self.handle_stats
            ),
            'random': CommandHandler(
                command='/random',
                description='随机推荐一个高分项目',
                callback=self.handle_random
            ),
            'trend': CommandHandler(
                command='/trend',
                description='查看近期技术趋势分析',
                callback=self.handle_trend
            ),
        }
    
    def start(self):
        if self.running:
            logger.warning("Command bot is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._poll_updates, daemon=True)
        self.thread.start()
        logger.info("Telegram command bot started")
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Telegram command bot stopped")
    
    def _poll_updates(self):
        while self.running:
            try:
                updates = self._get_updates()
                if updates:
                    for update in updates:
                        self._process_update(update)
                time.sleep(2)
            except Exception as e:
                logger.error(f"Error polling updates: {e}")
                time.sleep(5)
    
    def _get_updates(self) -> List[Dict]:
        url = f"{self.api_base}/getUpdates"
        params = {
            'offset': self.last_update_id + 1,
            'timeout': 10
        }
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if data.get('ok'):
            return data.get('result', [])
        return []
    
    def _process_update(self, update: Dict):
        self.last_update_id = update.get('update_id', 0)
        
        message = update.get('message')
        if not message:
            return
        
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        
        if not text.startswith('/'):
            return
        
        command = text.split()[0].lower()
        handler = self.commands.get(command.lstrip('/'))
        
        if handler:
            try:
                handler.callback(chat_id, text)
            except Exception as e:
                logger.error(f"Error handling command {command}: {e}")
                self.notifier.send_message(
                    "❌ 命令执行失败，请稍后重试",
                    chat_id=chat_id
                )
    
    def handle_start(self, chat_id: str, text: str):
        help_text = self._get_help_text()
        self.notifier.send_message(help_text, chat_id=chat_id)
    
    def handle_help(self, chat_id: str, text: str):
        help_text = self._get_help_text()
        self.notifier.send_message(help_text, chat_id=chat_id)
    
    def handle_top(self, chat_id: str, text: str):
        try:
            limit = int(text.split()[1]) if len(text.split()) > 1 else 5
            limit = min(limit, 10)
        except:
            limit = 5
        
        projects = self.db.get_top_scored_repositories(limit=limit, include_notified=True)
        if not projects:
            self.notifier.send_message("📭 暂无评分项目", chat_id=chat_id)
            return
        
        lines = ["🏆 *评分最高的项目*"]
        for i, (repo, score, analysis) in enumerate(projects, 1):
            stars = repo.stars
            score_val = score.total_score
            lines.append(f"{i}. 🌟 *{score_val:.0f}分* [{repo.full_name}]({repo.html_url}) ⭐{stars}")
            if analysis.problem_solved:
                problem = analysis.problem_solved[:40]
                if len(analysis.problem_solved) > 40:
                    problem += "..."
                lines.append(f"   _{problem}_")
        
        self.notifier.send_message("\n".join(lines), chat_id=chat_id)
    
    def handle_stars(self, chat_id: str, text: str):
        try:
            limit = int(text.split()[1]) if len(text.split()) > 1 else 5
            limit = min(limit, 10)
        except:
            limit = 5
        
        repos = self.db.get_repositories_by_stars(limit=limit)
        if not repos:
            self.notifier.send_message("📭 暂无项目数据", chat_id=chat_id)
            return
        
        lines = ["⭐ *Star 最多的项目*"]
        for i, repo in enumerate(repos, 1):
            stars = repo.stars
            lines.append(f"{i}. [{repo.full_name}]({repo.html_url}) ⭐{stars}")
            if repo.description:
                desc = repo.description[:40]
                if len(repo.description) > 40:
                    desc += "..."
                lines.append(f"   _{desc}_")
        
        self.notifier.send_message("\n".join(lines), chat_id=chat_id)
    
    def handle_new(self, chat_id: str, text: str):
        try:
            limit = int(text.split()[1]) if len(text.split()) > 1 else 5
            limit = min(limit, 10)
        except:
            limit = 5
        
        repos = self.db.get_repositories_by_date(limit=limit)
        if not repos:
            self.notifier.send_message("📭 暂无项目数据", chat_id=chat_id)
            return
        
        lines = ["🆕 *最新创建的项目*"]
        for i, repo in enumerate(repos, 1):
            stars = repo.stars
            created = repo.created_at.strftime('%Y-%m-%d') if repo.created_at else '未知'
            lines.append(f"{i}. [{repo.full_name}]({repo.html_url}) ⭐{stars} 创建于 {created}")
            if repo.description:
                desc = repo.description[:40]
                if len(repo.description) > 40:
                    desc += "..."
                lines.append(f"   _{desc}_")
        
        self.notifier.send_message("\n".join(lines), chat_id=chat_id)
    
    def handle_today(self, chat_id: str, text: str):
        today = datetime.now().date()
        projects = self.db.get_repositories_by_date_range(
            start_date=today, 
            end_date=today
        )
        
        if not projects:
            self.notifier.send_message("📭 今日暂无发现", chat_id=chat_id)
            return
        
        lines = ["📅 *今日发现的项目*"]
        for i, repo in enumerate(projects, 1):
            stars = repo.stars
            lines.append(f"{i}. [{repo.full_name}]({repo.html_url}) ⭐{stars}")
            if repo.description:
                desc = repo.description[:40]
                if len(repo.description) > 40:
                    desc += "..."
                lines.append(f"   _{desc}_")
        
        self.notifier.send_message("\n".join(lines), chat_id=chat_id)
    
    def handle_stats(self, chat_id: str, text: str):
        total_repos = self.db.get_total_repositories()
        analyzed_repos = self.db.get_total_analyzed_repositories()
        today_repos = self.db.get_today_repositories()
        
        stats_text = f"📊 *系统统计信息*\n\n"
        stats_text += f"📚 总项目数: {total_repos}\n"
        stats_text += f"🤖 已分析: {analyzed_repos}\n"
        stats_text += f"📅 今日新增: {today_repos}\n"
        stats_text += f"🔄 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self.notifier.send_message(stats_text, chat_id=chat_id)
    
    def handle_forks(self, chat_id: str, text: str):
        try:
            limit = int(text.split()[1]) if len(text.split()) > 1 else 5
            limit = min(limit, 10)
        except:
            limit = 5
        
        repos = self.db.get_repositories_by_forks(limit=limit)
        if not repos:
            self.notifier.send_message("📭 暂无项目数据", chat_id=chat_id)
            return
        
        lines = ["🍴 *Fork 最多的项目*"]
        for i, repo in enumerate(repos, 1):
            lines.append(f"{i}. [{repo.full_name}]({repo.html_url}) 🍴{repo.forks} ⭐{repo.stars}")
            if repo.description:
                desc = repo.description[:40]
                if len(repo.description) > 40:
                    desc += "..."
                lines.append(f"   _{desc}_")
        
        self.notifier.send_message("\n".join(lines), chat_id=chat_id)
    
    def handle_trending(self, chat_id: str, text: str):
        try:
            limit = int(text.split()[1]) if len(text.split()) > 1 else 5
            limit = min(limit, 10)
        except:
            limit = 5
        
        repos = self.db.get_repositories_by_growth(limit=limit)
        if not repos:
            self.notifier.send_message("📭 暂无增长数据", chat_id=chat_id)
            return
        
        lines = ["📈 *增长最快的项目*"]
        for i, (repo, growth) in enumerate(repos, 1):
            lines.append(f"{i}. [{repo.full_name}]({repo.html_url}) 📈{growth} ⭐{repo.stars}")
            if repo.description:
                desc = repo.description[:40]
                if len(repo.description) > 40:
                    desc += "..."
                lines.append(f"   _{desc}_")
        
        self.notifier.send_message("\n".join(lines), chat_id=chat_id)
    
    def handle_source(self, chat_id: str, text: str):
        parts = text.split()
        if len(parts) < 2:
            sources = self.db.get_available_sources()
            if sources:
                lines = ["📂 *可用来源:*"]
                for s in sources:
                    lines.append(f"  • {s}")
                lines.append("\n使用: /source github")
                self.notifier.send_message("\n".join(lines), chat_id=chat_id)
            else:
                self.notifier.send_message("📭 暂无来源数据", chat_id=chat_id)
            return
        
        source = parts[1].lower()
        try:
            limit = int(parts[2]) if len(parts) > 2 else 5
            limit = min(limit, 10)
        except:
            limit = 5
        
        repos = self.db.get_repositories_by_source(source=source, limit=limit)
        if not repos:
            self.notifier.send_message(f"📭 暂无 {source} 来源的项目", chat_id=chat_id)
            return
        
        lines = [f"📂 *{source.upper()} 来源项目*"]
        for i, repo in enumerate(repos, 1):
            lines.append(f"{i}. [{repo.full_name}]({repo.html_url}) ⭐{repo.stars}")
            if repo.description:
                desc = repo.description[:40]
                if len(repo.description) > 40:
                    desc += "..."
                lines.append(f"   _{desc}_")
        
        self.notifier.send_message("\n".join(lines), chat_id=chat_id)
    
    def handle_language(self, chat_id: str, text: str):
        parts = text.split()
        if len(parts) < 2:
            languages = self.db.get_available_languages()
            if languages:
                lines = ["💻 *可用语言:*"]
                for lang in languages[:10]:
                    lines.append(f"  • {lang}")
                if len(languages) > 10:
                    lines.append(f"  ... 共 {len(languages)} 种")
                lines.append("\n使用: /lang python")
                self.notifier.send_message("\n".join(lines), chat_id=chat_id)
            else:
                self.notifier.send_message("📭 暂无语言数据", chat_id=chat_id)
            return
        
        language = parts[1]
        try:
            limit = int(parts[2]) if len(parts) > 2 else 5
            limit = min(limit, 10)
        except:
            limit = 5
        
        repos = self.db.get_repositories_by_language(language=language, limit=limit)
        if not repos:
            self.notifier.send_message(f"📭 暂无 {language} 项目", chat_id=chat_id)
            return
        
        lines = [f"💻 *{language} 项目*"]
        for i, repo in enumerate(repos, 1):
            lines.append(f"{i}. [{repo.full_name}]({repo.html_url}) ⭐{repo.stars}")
            if repo.description:
                desc = repo.description[:40]
                if len(repo.description) > 40:
                    desc += "..."
                lines.append(f"   _{desc}_")
        
        self.notifier.send_message("\n".join(lines), chat_id=chat_id)
    
    def handle_search(self, chat_id: str, text: str):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            self.notifier.send_message("🔍 请输入搜索关键词\n用法: /search ai", chat_id=chat_id)
            return
        
        keyword = parts[1]
        repos = self.db.search_repositories(keyword=keyword, limit=10)
        if not repos:
            self.notifier.send_message(f"🔍 未找到包含 '{keyword}' 的项目", chat_id=chat_id)
            return
        
        lines = [f"🔍 *搜索结果: {keyword}*"]
        for i, repo in enumerate(repos, 1):
            lines.append(f"{i}. [{repo.full_name}]({repo.html_url}) ⭐{repo.stars}")
            if repo.description:
                desc = repo.description[:40]
                if len(repo.description) > 40:
                    desc += "..."
                lines.append(f"   _{desc}_")
        
        self.notifier.send_message("\n".join(lines), chat_id=chat_id)
    
    def handle_random(self, chat_id: str, text: str):
        import random
        
        projects = self.db.get_top_scored_repositories(limit=20)
        if not projects:
            self.notifier.send_message("📭 暂无项目数据", chat_id=chat_id)
            return
        
        repo, score, analysis = random.choice(projects)
        
        lines = ["🎲 *随机推荐*"]
        lines.append(f"🌟 *{score.total_score:.0f}分* [{repo.full_name}]({repo.html_url})")
        lines.append(f"⭐ {repo.stars} | 🍴 {repo.forks} | 💻 {repo.language or '未知'}")
        
        if repo.description:
            lines.append(f"\n📝 {repo.description}")
        
        if analysis and analysis.problem_solved:
            lines.append(f"\n🎯 *解决问题:* {analysis.problem_solved[:100]}")
        
        if analysis and analysis.monetization_potential:
            lines.append(f"\n💰 *变现潜力:* {analysis.monetization_potential[:100]}")
        
        self.notifier.send_message("\n".join(lines), chat_id=chat_id)
    
    def handle_trend(self, chat_id: str, text: str):
        try:
            parts = text.split()
            days = 7
            if len(parts) > 1:
                try:
                    days = int(parts[1])
                    days = max(1, min(days, 30))
                except ValueError:
                    pass
            
            analysis = self.trend_analyzer.analyze_trends(days=days)
            report = self.trend_analyzer.format_trend_report(analysis)
            self.notifier.send_message(report, chat_id=chat_id)
        except Exception as e:
            logger.error(f"Error in handle_trend: {e}")
            self.notifier.send_message("❌ 趋势分析失败，请稍后重试", chat_id=chat_id)
    
    def _get_help_text(self) -> str:
        help_text = "🤖 *GitHub 趋势雷达 - 命令帮助*\n\n"
        help_text += "以下是可用的命令：\n\n"
        
        for cmd, handler in self.commands.items():
            help_text += f"`/{cmd}` - {handler.description}\n"
        
        help_text += "\n🎯 *使用示例：*\n"
        help_text += "/top 10 - 查看评分最高的10个项目\n"
        help_text += "/stars 5 - 查看Star最多的5个项目\n"
        help_text += "/forks 5 - 查看Fork最多的5个项目\n"
        help_text += "/new - 查看最新创建的项目\n"
        help_text += "/today - 查看今日发现的项目\n"
        help_text += "/trending - 查看增长最快的项目\n"
        help_text += "/source github - 查看GitHub来源项目\n"
        help_text += "/lang python - 查看Python项目\n"
        help_text += "/search ai - 搜索包含ai的项目\n"
        help_text += "/random - 随机推荐一个高分项目\n"
        help_text += "/trend - 查看近期技术趋势分析\n"
        help_text += "/stats - 查看系统统计信息"
        
        return help_text
    
    def _set_commands_menu(self):
        """设置Telegram命令菜单"""
        url = f"{self.api_base}/setMyCommands"
        
        commands = []
        for cmd, handler in self.commands.items():
            commands.append({
                "command": cmd,
                "description": handler.description
            })
        
        payload = {
            "commands": commands
        }
        
        try:
            response = requests.post(url, json=payload, timeout=15)
            if response.ok:
                data = response.json()
                if data.get('ok'):
                    logger.info("Telegram command menu set successfully")
                else:
                    logger.error(f"Failed to set command menu: {data.get('description')}")
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error setting command menu: {e}")
