import json
import time
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from config import LLMConfig
from database.models import Repository, AnalysisResult
from utils.logger import get_logger
from utils.helpers import retry_on_failure

logger = get_logger(__name__)


@dataclass
class LLMAnalysisResult:
    problem_solved: str
    target_audience: str
    growth_reason: str
    copy_difficulty: str
    monetization_potential: str
    differentiation_ideas: List[str] = field(default_factory=list)
    copyability_score: float = 10.0
    monetization_score: float = 10.0
    differentiation_score: float = 10.0
    raw_response: str = ""
    is_fallback: bool = False
    error_message: str = ""


@dataclass
class AnalysisError:
    repo_name: str
    error_type: str
    error_message: str
    status_code: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)


ANALYSIS_PROMPT = """你是一位专业的产品经理和技术投资人，擅长分析开源项目的商业价值。

请分析以下 GitHub 项目，并给出结构化的商业分析报告。

## 项目信息
- 名称: {name}
- 描述: {description}
- 语言: {language}
- Stars: {stars}
- Topics: {topics}

## 项目内容摘要
{readme}

---

请严格按照以下 JSON 格式输出分析结果（不要输出其他内容，只输出 JSON）：

{{
    "problem_solved": "这个项目解决什么核心问题？（1-2句话）",
    "target_audience": "目标用户是谁？（开发者/企业/个人用户等）",
    "growth_reason": "为什么会增长？核心价值点是什么？",
    "copy_difficulty": "复制难度评估：低/中/高，并说明原因",
    "monetization_potential": "变现场景分析：是否有付费场景？可能的变现方式？",
    "differentiation_ideas": [
        "差异化方向1：例如中文版本",
        "差异化方向2：例如企业版",
        "差异化方向3：例如自动化增强版"
    ],
    "copyability_score": 0-20分（分数越高越容易复制），
    "monetization_score": 0-20分（分数越高变现潜力越大），
    "differentiation_score": 0-20分（分数越高差异化空间越大）
}}

评分标准：
- copyability_score: 纯前端/单文件脚本=15-20分，需要复杂后端=8-14分，需要GPU集群/复杂编译=0-7分
- monetization_score: 离钱近的场景(自动化/数据提取/UI生成)=15-20分，工具类=8-14分，纯娱乐/学习=0-7分
- differentiation_score: 有明确细分市场=15-20分，中等=8-14分，市场饱和=0-7分
"""

FALLBACK_PROMPT = """基于以下 GitHub 项目信息，快速判断其商业价值：

项目: {name}
描述: {description}
语言: {language}
Stars: {stars}
Topics: {topics}

请用一句话回答：这个项目主要解决什么问题？目标用户是谁？
"""


class LLMAnalyzer:
    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
    REQUEST_DELAY = 3.0
    MIN_README_LENGTH = 100
    
    MODEL_MAPPING = {
        'Google Gemini 2.5 Flash': 'gemini-2.5-flash',
        'Google Gemini 2.0 Flash': 'gemini-2.0-flash',
        'gemini-2.5-flash': 'gemini-2.5-flash',
        'gemini-2.0-flash': 'gemini-2.0-flash',
    }

    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key
        self.model_name = config.model
        self.model = self.MODEL_MAPPING.get(config.model, 'gemini-2.0-flash')
        self.session = requests.Session()
        self._last_request_time = 0
        self._error_log: List[AnalysisError] = []

    def _build_content_summary(self, repo: Repository) -> str:
        if repo.readme_content and len(repo.readme_content) >= self.MIN_README_LENGTH:
            return repo.readme_content[:6000]
        
        parts = []
        
        if repo.readme_content:
            parts.append(f"README摘要: {repo.readme_content[:500]}")
        
        if repo.description:
            parts.append(f"项目描述: {repo.description}")
        
        if repo.topics:
            parts.append(f"技术标签: {', '.join(repo.topics)}")
        
        if repo.language:
            parts.append(f"主要语言: {repo.language}")
        
        if not parts:
            return "该项目暂无详细描述信息。"
        
        return "\n".join(parts)

    def _log_error(self, repo_name: str, error_type: str, message: str, status_code: Optional[int] = None):
        error = AnalysisError(
            repo_name=repo_name,
            error_type=error_type,
            error_message=message,
            status_code=status_code
        )
        self._error_log.append(error)
        
        log_msg = f"[{error_type}] {repo_name}: {message}"
        if status_code:
            log_msg += f" (HTTP {status_code})"
        logger.error(log_msg)

    def get_error_log(self) -> List[AnalysisError]:
        return self._error_log.copy()

    def clear_error_log(self):
        self._error_log.clear()

    @retry_on_failure(max_retries=3, delay=5.0, exceptions=(requests.RequestException,))
    def _call_api(self, prompt: str) -> tuple:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - elapsed)
        
        url = f"{self.API_BASE}/{self.model}:generateContent"
        params = {"key": self.api_key}
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
            }
        }
        
        response = self.session.post(url, params=params, json=payload, timeout=60)
        status_code = response.status_code
        
        self._last_request_time = time.time()
        
        if response.status_code == 429:
            return None, "rate_limit", "API 速率限制，请稍后重试", 429
        
        response.raise_for_status()
        
        data = response.json()
        
        if "candidates" in data and len(data["candidates"]) > 0:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        return part["text"], None, None, 200
        
        if "error" in data:
            error_msg = data["error"].get("message", "Unknown API error")
            return None, "api_error", error_msg, status_code
        
        return None, "parse_error", f"Unexpected response: {str(data)[:200]}", status_code

    def _generate_fallback_result(self, repo: Repository, error_msg: str = "") -> LLMAnalysisResult:
        problem = "无法分析（LLM 服务不可用）"
        audience = "未知"
        
        if repo.description:
            problem = repo.description[:100]
        
        if repo.topics:
            audience = f"对 {', '.join(repo.topics[:3])} 感兴趣的开发者"
        elif repo.language:
            audience = f"{repo.language} 开发者"
        
        copy_score = 10.0
        if repo.language in ["JavaScript", "TypeScript", "Python", "Go"]:
            copy_score = 15.0
        elif repo.language in ["Rust", "C++", "C"]:
            copy_score = 7.0
        
        monetization_score = 8.0
        if any(t in repo.topics for t in ["api", "automation", "cli", "tool"]):
            monetization_score = 14.0
        
        return LLMAnalysisResult(
            problem_solved=problem,
            target_audience=audience,
            growth_reason="基于项目基本信息推测",
            copy_difficulty="未知（LLM 分析失败）",
            monetization_potential="需要进一步人工分析",
            differentiation_ideas=["中文版本", "企业版本", "自动化增强版"],
            copyability_score=copy_score,
            monetization_score=monetization_score,
            differentiation_score=10.0,
            raw_response="",
            is_fallback=True,
            error_message=error_msg
        )

    def analyze_repository(self, repo: Repository) -> LLMAnalysisResult:
        content_summary = self._build_content_summary(repo)
        
        prompt = ANALYSIS_PROMPT.format(
            name=repo.full_name,
            description=repo.description or "无描述",
            language=repo.language or "未知",
            stars=repo.stars,
            topics=', '.join(repo.topics) if repo.topics else "无",
            readme=content_summary
        )

        try:
            raw_response, error_type, error_msg, status_code = self._call_api(prompt)
            
            if error_type:
                self._log_error(repo.full_name, error_type, error_msg, status_code)
                
                if error_type == "rate_limit":
                    logger.warning(f"Rate limit hit for {repo.full_name}, using fallback")
                    return self._generate_fallback_result(repo, error_msg)
                
                return self._generate_fallback_result(repo, error_msg)
            
            if not raw_response:
                self._log_error(repo.full_name, "empty_response", "API returned empty response")
                return self._generate_fallback_result(repo, "Empty API response")
            
            result = self._parse_response(raw_response)
            
            if result:
                result.raw_response = raw_response
                logger.info(f"Successfully analyzed {repo.full_name}")
                return result
            else:
                self._log_error(repo.full_name, "parse_failed", "Failed to parse LLM response")
                return self._generate_fallback_result(repo, "Failed to parse response")
            
        except requests.RequestException as e:
            self._log_error(repo.full_name, "network_error", str(e))
            return self._generate_fallback_result(repo, str(e))
        except Exception as e:
            self._log_error(repo.full_name, "unknown_error", str(e))
            return self._generate_fallback_result(repo, str(e))

    def _parse_response(self, response: str) -> Optional[LLMAnalysisResult]:
        try:
            json_match = response
            if '```json' in response:
                json_match = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                json_match = response.split('```')[1].split('```')[0]
            
            data = json.loads(json_match.strip())
            
            def safe_float(value, default=10.0):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default
            
            return LLMAnalysisResult(
                problem_solved=data.get('problem_solved', ''),
                target_audience=data.get('target_audience', ''),
                growth_reason=data.get('growth_reason', ''),
                copy_difficulty=data.get('copy_difficulty', ''),
                monetization_potential=data.get('monetization_potential', ''),
                differentiation_ideas=data.get('differentiation_ideas', []),
                copyability_score=safe_float(data.get('copyability_score'), 10.0),
                monetization_score=safe_float(data.get('monetization_score'), 10.0),
                differentiation_score=safe_float(data.get('differentiation_score'), 10.0),
                raw_response=response,
                is_fallback=False
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._extract_fields_from_text(response)

    def _extract_fields_from_text(self, text: str) -> Optional[LLMAnalysisResult]:
        import re
        
        def extract_field(name: str) -> str:
            pattern = rf'"{name}"\s*:\s*"([^"]*)"'
            match = re.search(pattern, text)
            return match.group(1) if match else ""
        
        return LLMAnalysisResult(
            problem_solved=extract_field('problem_solved'),
            target_audience=extract_field('target_audience'),
            growth_reason=extract_field('growth_reason'),
            copy_difficulty=extract_field('copy_difficulty'),
            monetization_potential=extract_field('monetization_potential'),
            differentiation_ideas=[],
            copyability_score=10.0,
            monetization_score=10.0,
            differentiation_score=10.0,
            raw_response=text,
            is_fallback=False
        )

    def to_analysis_result(self, llm_result: LLMAnalysisResult, repo_id: int) -> AnalysisResult:
        return AnalysisResult(
            repo_id=repo_id,
            problem_solved=llm_result.problem_solved,
            target_audience=llm_result.target_audience,
            growth_reason=llm_result.growth_reason,
            copy_difficulty=llm_result.copy_difficulty,
            monetization_potential=llm_result.monetization_potential,
            differentiation_ideas=llm_result.differentiation_ideas,
            raw_llm_response=llm_result.raw_response,
            analyzed_at=datetime.now(),
            is_fallback=llm_result.is_fallback
        )
