import requests
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
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.api_base = f"https://api.telegram.org/bot{config.bot_token}"

    @retry_on_failure(max_retries=3, delay=2.0, exceptions=(requests.RequestException,))
    def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True
    ) -> Optional[int]:
        target_chat_id = chat_id or self.config.chat_id
        
        url = f"{self.api_base}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                message_id = data["result"]["message_id"]
                logger.info(f"Message sent successfully, message_id: {message_id}")
                return message_id
            else:
                logger.error(f"Failed to send message: {data.get('description')}")
                return None
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
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
        
        return self.send_message(text)

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
