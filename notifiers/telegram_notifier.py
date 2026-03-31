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
        disable_web_page_preview: bool = True
    ) -> Optional[int]:
        elapsed = time.time() - self._last_message_time
        if elapsed < self.MIN_MESSAGE_INTERVAL:
            sleep_time = self.MIN_MESSAGE_INTERVAL - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        # 尝试的chat_id列表
        chat_ids_to_try = []
        
        # 首先尝试提供的chat_id
        if chat_id:
            chat_ids_to_try.append(chat_id)
        
        # 然后尝试配置中的chat_id
        if self.config.chat_id:
            chat_ids_to_try.append(self.config.chat_id)
        
        # 最后尝试配置中的channel_id
        if self.config.channel_id:
            chat_ids_to_try.append(self.config.channel_id)
        
        # 去重
        chat_ids_to_try = list(set(chat_ids_to_try))
        
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
            return "📭 今日暂无高分项目发现"
        
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
        
        # 先尝试使用chat_id
        msg_id = self.send_message(text)
        if msg_id:
            return msg_id
        
        # 如果失败，尝试使用channel_id
        if self.config.channel_id:
            logger.info("Trying channel_id instead of chat_id")
            msg_id = self.send_message(text, chat_id=self.config.channel_id)
            if msg_id:
                return msg_id
        
        return None

    def notify_batch(
        self,
        projects: List[tuple],
        send_summary: bool = True
    ) -> List[int]:
        message_ids = []
        
        if send_summary and len(projects) > 3:
            summary = self.format_daily_summary(projects)
            msg_id = self.send_message(summary)
            if msg_id:
                message_ids.append(msg_id)
        else:
            for repo, score, analysis in projects:
                msg_id = self.notify_project(repo, score, analysis)
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
