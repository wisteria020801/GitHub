import requests
import time
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from config import TelegramConfig
from database.models import Repository, Score, AnalysisResult
from utils.logger import get_logger
from utils.helpers import format_number, retry_on_failure

logger = get_logger(__name__)


@dataclass
class TelegramMessage:
    text: str
    parse_mode: str = "Markdown"
    disable_web_page_preview: bool = False


class TelegramNotifier:
    MIN_MESSAGE_INTERVAL = 1.0
    
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.api_base = f"https://api.telegram.org/bot{config.bot_token}"
        self._last_message_time = 0

    @retry_on_failure(max_retries=3, delay=2.0, exceptions=(requests.RequestException,))
    def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True,
        prefer_channel: bool = False
    ) -> Optional[int]:
        elapsed = time.time() - self._last_message_time
        if elapsed < self.MIN_MESSAGE_INTERVAL:
            sleep_time = self.MIN_MESSAGE_INTERVAL - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        chat_ids_to_try = []
        
        if chat_id:
            chat_ids_to_try.append(chat_id)
        elif prefer_channel:
            # 优先发送到群聊
            if self.config.channel_id:
                chat_ids_to_try.append(self.config.channel_id)
            # 如果没有群聊配置，或者群聊发送失败，尝试私聊
            if self.config.chat_id:
                chat_ids_to_try.append(self.config.chat_id)
        else:
            # 正常模式：先尝试群聊，再尝试私聊
            if self.config.channel_id:
                chat_ids_to_try.append(self.config.channel_id)
            if self.config.chat_id:
                chat_ids_to_try.append(self.config.chat_id)
        
        chat_ids_to_try = list(dict.fromkeys(chat_ids_to_try))
        
        for target_chat_id in chat_ids_to_try:
            url = f"{self.api_base}/sendMessage"
            payload = {
                "chat_id": target_chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_web_page_preview
            }
            
            try:
                response = requests.post(url, json=payload, timeout=30)
                if not response.ok:
                    logger.error(f"Telegram API error for chat_id {target_chat_id}: {response.status_code} - {response.text}")
                    continue
                data = response.json()
                
                if data.get("ok"):
                    message_id = data["result"]["message_id"]
                    self._last_message_time = time.time()
                    logger.info(f"Message sent successfully to chat_id {target_chat_id}, message_id: {message_id}")
                    return message_id
                else:
                    logger.error(f"Failed to send message to chat_id {target_chat_id}: {data.get('description')}")
                    continue
            except requests.RequestException as e:
                logger.error(f"Failed to send Telegram message to chat_id {target_chat_id}: {e}")
                continue
        
        return None

    def format_project_card(
        self,
        repo: Repository,
        score: Score,
        analysis: AnalysisResult
    ) -> str:
        stars_str = format_number(repo.stars)
        forks_str = format_number(repo.forks)
        
        score_emoji = self._get_score_emoji(score.total_score)
        
        card = f"""🚀 *{repo.full_name}*
{score_emoji} *评分: {score.total_score:.0f}/100*

📌 *解决的问题*
{analysis.problem_solved or '暂无分析'}

👥 *目标用户*
{analysis.target_audience or '暂无分析'}

💰 *变现场景*
{analysis.monetization_potential or '暂无分析'}

📊 *数据*
⭐ {stars_str} stars | 🍴 {forks_str} forks
🔤 {repo.language or '未知'}

🔗 [查看项目]({repo.html_url})
"""
        return card

    def format_simple_card(
        self,
        repo: Repository,
        score: Score,
        analysis: AnalysisResult
    ) -> str:
        stars_str = format_number(repo.stars)
        score_emoji = self._get_score_emoji(score.total_score)
        
        ideas_text = ""
        if analysis.differentiation_ideas:
            ideas_text = "\n".join([f"  • {idea}" for idea in analysis.differentiation_ideas[:3]])
        
        card = f"""🚀 *{repo.full_name}*
{score_emoji} *{score.total_score:.0f}分* | ⭐ {stars_str} | 🔤 {repo.language or '未知'}

📝 {analysis.problem_solved or repo.description or '暂无描述'}

💡 *差异化方向*
{ideas_text or '暂无建议'}

🔗 [查看项目]({repo.html_url})
"""
        return card

    def format_daily_summary(
        self,
        projects: List[tuple]
    ) -> str:
        if not projects:
            return "📭 *今日暂无新的高分项目发现*\n\n💡 系统正常运行中，继续监控中..."
        
        lines = ["📊 *今日 GitHub 高分项目速报*\n"]
        
        for i, (repo, score, analysis) in enumerate(projects[:10], 1):
            score_emoji = self._get_score_emoji(score.total_score)
            stars_str = format_number(repo.stars)
            
            lines.append(
                f"{i}. {score_emoji} *{score.total_score:.0f}分* "
                f"[{repo.full_name}]({repo.html_url}) "
                f"⭐{stars_str}"
            )
            
            if analysis.problem_solved:
                problem = analysis.problem_solved[:50]
                if len(analysis.problem_solved) > 50:
                    problem += "..."
                lines.append(f"   _{problem}_")
            
            lines.append("")
        
        return "\n".join(lines)

    def notify_project(
        self,
        repo: Repository,
        score: Score,
        analysis: AnalysisResult,
        use_simple: bool = True
    ) -> Optional[int]:
        if use_simple:
            text = self.format_simple_card(repo, score, analysis)
        else:
            text = self.format_project_card(repo, score, analysis)
        
        msg_id = self.send_message(text, prefer_channel=True)
        return msg_id

    def notify_batch(
        self,
        projects: List[tuple],
        send_summary: bool = True
    ) -> List[int]:
        message_ids = []
        
        if send_summary and len(projects) > 3:
            summary = self.format_daily_summary(projects)
            msg_id = self.send_message(summary, prefer_channel=True)
            if msg_id:
                message_ids.append(msg_id)
        else:
            for repo, score, analysis in projects:
                msg_id = self.notify_project(repo, score, analysis)
                if msg_id:
                    message_ids.append(msg_id)
        
        return message_ids

    def notify_no_new_projects(self) -> Optional[int]:
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        text = f"""📭 *今日暂无新的高分项目发现*

🕐 扫描时间: {now}
💡 系统正常运行中，继续监控中...

📋 *你可以试试这些命令：*
• `/top` — 查看历史高分项目排行
• `/stars` — 查看Star最多的项目
• `/trending` — 查看增长最快的新项目
• `/new` — 查看最新收录的项目
• `/random` — 随机推荐一个高分项目
• `/stats` — 查看系统统计信息"""
        return self.send_message(text, prefer_channel=True)
    
    def format_growth_card(self, repo: Repository, growth: int, growth_rate: float) -> str:
        stars_str = format_number(repo.stars)
        growth_str = format_number(growth)
        
        card = f"""📈 *{repo.full_name}*
📊 *增长速度快* | ⬆️ +{growth_str} stars
📈 *增长率: {growth_rate:.1f}%* | ⭐ {stars_str}

📝 {repo.description or '暂无描述'}

🔗 [查看项目]({repo.html_url})
"""
        return card
    
    def notify_fast_growing_projects(self, projects: list) -> List[int]:
        """通知增长速度快的项目
        
        Args:
            projects: 项目列表，包含 (Repository, 增长数, 增长率) 元组
            
        Returns:
            消息ID列表
        """
        message_ids = []
        
        if not projects:
            return message_ids
        
        # 发送增长项目摘要
        summary_lines = ["📈 *快速增长项目速报*\n"]
        for i, (repo, growth, growth_rate) in enumerate(projects[:5], 1):
            stars_str = format_number(repo.stars)
            growth_str = format_number(growth)
            summary_lines.append(
                f"{i}. 📊 *{growth_rate:.1f}%* +{growth_str} stars "
                f"[{repo.full_name}]({repo.html_url}) "
                f"⭐{stars_str}"
            )
        summary = "\n".join(summary_lines)
        msg_id = self.send_message(summary, prefer_channel=True)
        if msg_id:
            message_ids.append(msg_id)
        
        # 发送详细卡片
        for repo, growth, growth_rate in projects[:3]:
            text = self.format_growth_card(repo, growth, growth_rate)
            msg_id = self.send_message(text, prefer_channel=True)
            if msg_id:
                message_ids.append(msg_id)
        
        return message_ids

    def _get_score_emoji(self, score: float) -> str:
        if score >= 80:
            return "🌟"
        elif score >= 70:
            return "👍"
        elif score >= 60:
            return "😊"
        elif score >= 50:
            return "🤔"
        else:
            return "⚠️"

    def test_connection(self) -> bool:
        try:
            url = f"{self.api_base}/getMe"
            response = requests.get(url, timeout=10)
            data = response.json()
            if data.get("ok"):
                bot_info = data["result"]
                logger.info(f"Telegram bot connected: @{bot_info.get('username')}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False
