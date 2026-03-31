"""
LLM提示词填充服务

自动分析项目并填充提示词变量，生成可直接使用的提示词
"""
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from utils.logger import get_logger
from analyzers.llm_analyzer import LLMAnalyzer
from generators.prompts.prompt_manager import prompt_manager

logger = get_logger(__name__)


@dataclass
class FilledPrompts:
    """填充后的提示词集合"""
    project_name: str
    code_generation: str
    differentiation: str
    tech_stack: str
    monetization: str
    analysis_summary: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    llm_used: str = ""
    token_usage: int = 0


class LLMPromptFiller:
    """LLM提示词填充器"""
    
    def __init__(self):
        self.llm_analyzer = LLMAnalyzer()
    
    def fill_prompts(
        self,
        project_name: str,
        description: str,
        stars: int = 0,
        language: str = "Unknown",
        topics: Optional[List[str]] = None,
        readme_preview: str = "",
        existing_analysis: Optional[Dict[str, Any]] = None
    ) -> FilledPrompts:
        """分析项目并填充所有提示词"""
        
        logger.info(f"Starting LLM prompt filling for: {project_name}")
        
        analysis = existing_analysis or self._analyze_project(
            project_name=project_name,
            description=description,
            stars=stars,
            language=language,
            topics=topics or [],
            readme_preview=readme_preview
        )
        
        filled_prompts = self._fill_all_prompts(
            project_name=project_name,
            description=description,
            analysis=analysis,
            language=language
        )
        
        return FilledPrompts(
            project_name=project_name,
            code_generation=filled_prompts["code_generation"],
            differentiation=filled_prompts["differentiation"],
            tech_stack=filled_prompts["tech_stack"],
            monetization=filled_prompts["monetization"],
            analysis_summary=analysis,
            llm_used=self.llm_analyzer.model_name if hasattr(self.llm_analyzer, 'model_name') else "gemini",
            token_usage=0
        )
    
    def _analyze_project(
        self,
        project_name: str,
        description: str,
        stars: int,
        language: str,
        topics: List[str],
        readme_preview: str
    ) -> Dict[str, Any]:
        """使用LLM分析项目"""
        
        analysis_prompt = self._build_analysis_prompt(
            project_name=project_name,
            description=description,
            stars=stars,
            language=language,
            topics=topics,
            readme_preview=readme_preview
        )
        
        try:
            llm_response = self.llm_analyzer.analyze(
                readme_content=readme_preview or description,
                repo_name=project_name,
                extra_context={
                    "stars": stars,
                    "language": language,
                    "topics": topics,
                    "analysis_focus": "prompt_filling"
                }
            )
            
            return self._parse_llm_response(llm_response)
            
        except Exception as e:
            logger.warning(f"LLM analysis failed, using fallback: {e}")
            return self._get_fallback_analysis(
                project_name=project_name,
                description=description,
                language=language,
                topics=topics
            )
    
    def _build_analysis_prompt(
        self,
        project_name: str,
        description: str,
        stars: int,
        language: str,
        topics: List[str],
        readme_preview: str
    ) -> str:
        """构建分析提示词"""
        return f"""分析以下开源项目，提取关键信息用于生成MVP项目骨架：

项目名称: {project_name}
描述: {description}
Star数: {stars}
主要语言: {language}
标签: {', '.join(topics) if topics else '无'}
README预览: {readme_preview[:1000] if readme_preview else '无'}

请以JSON格式输出以下字段：
1. core_features: 核心功能列表（3-5个）
2. target_audience: 目标用户群体
3. problem_solved: 解决的核心问题
4. monetization_potential: 变现潜力评估
5. differentiation_ideas: 差异化方向建议（3-5个）
6. tech_stack_recommendation: 推荐技术栈
7. competitors: 主要竞品
8. market_size: 市场规模评估

只输出JSON，不要其他内容。"""
    
    def _parse_llm_response(self, response: Any) -> Dict[str, Any]:
        """解析LLM响应"""
        if isinstance(response, dict):
            return response
        
        if isinstance(response, str):
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        return {}
    
    def _get_fallback_analysis(
        self,
        project_name: str,
        description: str,
        language: str,
        topics: List[str]
    ) -> Dict[str, Any]:
        """获取备用分析结果"""
        return {
            "core_features": ["核心功能1", "核心功能2", "核心功能3"],
            "target_audience": "开发者",
            "problem_solved": description[:100] if description else "待分析",
            "monetization_potential": "中等",
            "differentiation_ideas": [
                "中文本地化版本",
                "增加Telegram推送",
                "添加付费订阅功能"
            ],
            "tech_stack_recommendation": f"{language}, FastAPI, SQLite",
            "competitors": "待分析",
            "market_size": "中等规模"
        }
    
    def _fill_all_prompts(
        self,
        project_name: str,
        description: str,
        analysis: Dict[str, Any],
        language: str
    ) -> Dict[str, str]:
        """填充所有提示词"""
        
        core_features = ", ".join(analysis.get("core_features", []))
        target_audience = analysis.get("target_audience", "开发者")
        problem_solved = analysis.get("problem_solved", "")
        monetization = analysis.get("monetization_potential", "")
        differentiation = "\n".join([f"- {idea}" for idea in analysis.get("differentiation_ideas", [])])
        tech_stack = analysis.get("tech_stack_recommendation", f"{language}, FastAPI")
        competitors = analysis.get("competitors", "")
        
        code_gen_prompt = prompt_manager.get_code_generation_prompt(
            project_name=project_name,
            description=description,
            core_features=core_features,
            tech_stack=tech_stack,
            monetization=monetization,
            differentiation=differentiation
        )
        
        diff_prompt = prompt_manager.get_differentiation_prompt(
            project_name=project_name,
            description=description,
            core_features=core_features,
            target_audience=target_audience,
            competitors=competitors,
            tech_stack=tech_stack
        )
        
        tech_prompt = prompt_manager.get_tech_stack_prompt(
            project_name=project_name,
            project_type="API服务",
            core_features=core_features
        )
        
        monet_prompt = prompt_manager.get_monetization_prompt(
            project_name=project_name,
            description=description,
            target_audience=target_audience,
            core_features=core_features,
            problem_solved=problem_solved
        )
        
        return {
            "code_generation": code_gen_prompt,
            "differentiation": diff_prompt,
            "tech_stack": tech_prompt,
            "monetization": monet_prompt
        }
    
    def fill_from_repo(self, repo_id: int) -> Optional[FilledPrompts]:
        """从数据库仓库填充提示词"""
        from database.db_manager import DatabaseManager
        
        db = DatabaseManager()
        
        repo = db.get_repository_by_id(repo_id)
        if not repo:
            logger.error(f"Repository not found: {repo_id}")
            return None
        
        analysis = db.get_analysis_by_repo_id(repo_id)
        analysis_dict = {}
        if analysis:
            analysis_dict = {
                "core_features": analysis.core_features if hasattr(analysis, 'core_features') else [],
                "target_audience": analysis.target_audience if hasattr(analysis, 'target_audience') else "",
                "problem_solved": analysis.problem_solved if hasattr(analysis, 'problem_solved') else "",
                "monetization_potential": analysis.monetization_potential if hasattr(analysis, 'monetization_potential') else "",
                "differentiation_ideas": analysis.differentiation_ideas if hasattr(analysis, 'differentiation_ideas') and analysis.differentiation_ideas else []
            }
        
        return self.fill_prompts(
            project_name=repo.name,
            description=repo.description or "",
            stars=repo.stars or 0,
            language=repo.language or "Unknown",
            topics=repo.topics if hasattr(repo, 'topics') and repo.topics else [],
            readme_preview=repo.readme_content[:2000] if hasattr(repo, 'readme_content') and repo.readme_content else "",
            existing_analysis=analysis_dict if analysis_dict else None
        )


def quick_fill_prompts(
    project_name: str,
    description: str,
    language: str = "Python"
) -> FilledPrompts:
    """快速填充提示词（简化版）"""
    filler = LLMPromptFiller()
    
    return filler.fill_prompts(
        project_name=project_name,
        description=description,
        language=language,
        existing_analysis={
            "core_features": ["数据处理", "API服务", "自动化"],
            "target_audience": "开发者",
            "problem_solved": description[:100],
            "monetization_potential": "中等",
            "differentiation_ideas": ["中文版", "Telegram推送", "付费订阅"],
            "tech_stack_recommendation": f"{language}, FastAPI, SQLite"
        }
    )


if __name__ == "__main__":
    result = quick_fill_prompts(
        project_name="Test Project",
        description="A test project for demonstration",
        language="Python"
    )
    
    print(f"Project: {result.project_name}")
    print(f"Prompts generated: {len([result.code_generation, result.differentiation, result.tech_stack, result.monetization])}")
    print(f"Code generation prompt length: {len(result.code_generation)}")
