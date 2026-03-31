"""
增强版MVP生成器

整合所有提示词，提供完整的分析和生成能力
支持LLM自动填充提示词
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from utils.logger import get_logger
from generators.mvp_generator import MVPGenerator, GeneratedProject
from generators.prompts.prompt_manager import prompt_manager
from generators.prompts.llm_prompt_filler import LLMPromptFiller, FilledPrompts

logger = get_logger(__name__)


@dataclass
class AnalysisResult:
    project_name: str
    description: str
    target_audience: str
    core_features: List[str]
    tech_stack: str
    monetization_potential: str
    differentiation_ideas: List[str]
    problem_solved: str
    competitors: str = ""


@dataclass
class EnhancedGenerationResult:
    project_name: str
    analysis: AnalysisResult
    generated_project: Optional[GeneratedProject]
    prompts_used: Dict[str, str]
    created_at: datetime = field(default_factory=datetime.now)


class EnhancedMVPGenerator:
    """增强版MVP生成器"""
    
    def __init__(self, output_dir: Optional[str] = None, use_llm: bool = True):
        self.base_generator = MVPGenerator()
        self.llm_filler = LLMPromptFiller() if use_llm else None
        self.use_llm = use_llm
        if output_dir:
            self.base_generator.OUTPUT_DIR = Path(output_dir)
    
    def analyze_and_generate(
        self,
        project_name: str,
        description: str,
        target_audience: str,
        core_features: List[str],
        tech_stack: str = "Python",
        monetization_potential: str = "",
        differentiation_ideas: Optional[List[str]] = None,
        problem_solved: str = "",
        competitors: str = "",
        project_type: str = "api"
    ) -> EnhancedGenerationResult:
        """分析项目并生成骨架"""
        
        analysis = AnalysisResult(
            project_name=project_name,
            description=description,
            target_audience=target_audience,
            core_features=core_features,
            tech_stack=tech_stack,
            monetization_potential=monetization_potential,
            differentiation_ideas=differentiation_ideas or [],
            problem_solved=problem_solved,
            competitors=competitors
        )
        
        prompts_used = self._generate_all_prompts(analysis)
        
        project = self.base_generator.generate(
            project_name=project_name,
            project_type=project_type,
            analysis_result={
                "summary": description,
                "business_potential": target_audience,
                "differentiation": "\n".join(differentiation_ideas) if differentiation_ideas else "",
                "monetization": monetization_potential,
                "tech_stack": tech_stack,
                "core_features": ", ".join(core_features)
            }
        )
        
        self._save_analysis_prompts(project, prompts_used)
        
        return EnhancedGenerationResult(
            project_name=project_name,
            analysis=analysis,
            generated_project=project,
            prompts_used=prompts_used
        )
    
    def generate_with_llm(
        self,
        project_name: str,
        description: str,
        stars: int = 0,
        language: str = "Python",
        topics: Optional[List[str]] = None,
        readme_preview: str = "",
        project_type: str = "api"
    ) -> EnhancedGenerationResult:
        """使用LLM自动分析并生成项目骨架"""
        
        if not self.llm_filler:
            logger.warning("LLM filler not available, falling back to basic generation")
            return self.analyze_and_generate(
                project_name=project_name,
                description=description,
                target_audience="开发者",
                core_features=[],
                tech_stack=language,
                project_type=project_type
            )
        
        logger.info(f"Generating with LLM for: {project_name}")
        
        filled_prompts = self.llm_filler.fill_prompts(
            project_name=project_name,
            description=description,
            stars=stars,
            language=language,
            topics=topics or [],
            readme_preview=readme_preview
        )
        
        analysis = AnalysisResult(
            project_name=project_name,
            description=description,
            target_audience=filled_prompts.analysis_summary.get("target_audience", "开发者"),
            core_features=filled_prompts.analysis_summary.get("core_features", []),
            tech_stack=filled_prompts.analysis_summary.get("tech_stack_recommendation", language),
            monetization_potential=filled_prompts.analysis_summary.get("monetization_potential", ""),
            differentiation_ideas=filled_prompts.analysis_summary.get("differentiation_ideas", []),
            problem_solved=filled_prompts.analysis_summary.get("problem_solved", "")
        )
        
        project = self.base_generator.generate(
            project_name=project_name,
            project_type=project_type,
            analysis_result={
                "summary": description,
                "business_potential": analysis.target_audience,
                "differentiation": "\n".join(analysis.differentiation_ideas),
                "monetization": analysis.monetization_potential,
                "tech_stack": analysis.tech_stack,
                "core_features": ", ".join(analysis.core_features)
            }
        )
        
        prompts_used = {
            "code_generation": filled_prompts.code_generation,
            "differentiation": filled_prompts.differentiation,
            "tech_stack": filled_prompts.tech_stack,
            "monetization": filled_prompts.monetization
        }
        
        self._save_analysis_prompts(project, prompts_used)
        
        self._save_llm_analysis(project, filled_prompts.analysis_summary)
        
        logger.info(f"LLM generation complete for: {project_name}")
        
        return EnhancedGenerationResult(
            project_name=project_name,
            analysis=analysis,
            generated_project=project,
            prompts_used=prompts_used
        )
    
    def _save_llm_analysis(
        self, 
        project: GeneratedProject, 
        analysis: Dict[str, Any]
    ) -> None:
        """保存LLM分析结果"""
        output_path = Path(project.output_path)
        analysis_file = output_path / ".prompts" / "llm_analysis.json"
        
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved LLM analysis to {analysis_file}")
    
    def _generate_all_prompts(self, analysis: AnalysisResult) -> Dict[str, str]:
        """生成所有提示词"""
        prompts = {}
        
        prompts["code_generation"] = prompt_manager.get_code_generation_prompt(
            project_name=analysis.project_name,
            description=analysis.description,
            core_features=", ".join(analysis.core_features),
            tech_stack=analysis.tech_stack,
            monetization=analysis.monetization_potential,
            differentiation="\n".join(analysis.differentiation_ideas)
        )
        
        prompts["differentiation"] = prompt_manager.get_differentiation_prompt(
            project_name=analysis.project_name,
            description=analysis.description,
            core_features=", ".join(analysis.core_features),
            target_audience=analysis.target_audience,
            competitors=analysis.competitors,
            tech_stack=analysis.tech_stack
        )
        
        prompts["tech_stack"] = prompt_manager.get_tech_stack_prompt(
            project_name=analysis.project_name,
            project_type="API服务",
            core_features=", ".join(analysis.core_features)
        )
        
        prompts["monetization"] = prompt_manager.get_monetization_prompt(
            project_name=analysis.project_name,
            description=analysis.description,
            target_audience=analysis.target_audience,
            core_features=", ".join(analysis.core_features),
            problem_solved=analysis.problem_solved
        )
        
        return prompts
    
    def _save_analysis_prompts(
        self, 
        project: GeneratedProject, 
        prompts: Dict[str, str]
    ) -> None:
        """保存分析提示词到项目目录"""
        output_path = Path(project.output_path)
        prompts_dir = output_path / ".prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        
        for name, content in prompts.items():
            prompt_file = prompts_dir / f"{name}.md"
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(content)
        
        index_content = self._generate_prompts_index(prompts)
        index_file = prompts_dir / "README.md"
        with open(index_file, "w", encoding="utf-8") as f:
            f.write(index_content)
        
        logger.info(f"Saved {len(prompts)} prompts to {prompts_dir}")
    
    def _generate_prompts_index(self, prompts: Dict[str, str]) -> str:
        """生成提示词索引"""
        lines = [
            "# 项目生成提示词",
            "",
            "本目录包含生成此项目时使用的所有提示词。",
            "",
            "## 提示词列表",
            ""
        ]
        
        prompt_descriptions = {
            "code_generation": "代码生成 - 生成项目骨架的核心提示词",
            "differentiation": "差异化分析 - 分析项目的差异化方向",
            "tech_stack": "技术栈选择 - 推荐最优技术栈",
            "monetization": "变现策略 - 设计商业模式和定价"
        }
        
        for name, content in prompts.items():
            desc = prompt_descriptions.get(name, name)
            lines.append(f"### [{name}.md](./{name}.md)")
            lines.append(f"{desc}")
            lines.append(f"字符数: {len(content)}")
            lines.append("")
        
        lines.extend([
            "## 使用方法",
            "",
            "这些提示词可以：",
            "1. 直接复制到LLM（如Claude、GPT-4）中使用",
            "2. 作为进一步优化的基础",
            "3. 用于理解项目的设计思路",
            "",
            "## 下一步",
            "",
            "1. 将提示词发送给LLM获取详细建议",
            "2. 根据建议完善TODO标记的代码",
            "3. 实现变现功能",
            ""
        ])
        
        return "\n".join(lines)
    
    def generate_from_repo(
        self, 
        repo_id: int,
        project_type: str = "api",
        use_llm: bool = True
    ) -> Optional[EnhancedGenerationResult]:
        """从数据库仓库生成"""
        from database.db_manager import DatabaseManager
        
        db = DatabaseManager()
        
        repo = db.get_repository_by_id(repo_id)
        if not repo:
            logger.error(f"Repository not found: {repo_id}")
            return None
        
        if use_llm and self.llm_filler:
            return self.generate_with_llm(
                project_name=repo.name,
                description=repo.description or "",
                stars=repo.stars or 0,
                language=repo.language or "Python",
                topics=repo.topics if hasattr(repo, 'topics') and repo.topics else [],
                readme_preview=repo.readme_content[:2000] if hasattr(repo, 'readme_content') and repo.readme_content else "",
                project_type=project_type
            )
        
        analysis = db.get_analysis_by_repo_id(repo_id)
        
        return self.analyze_and_generate(
            project_name=repo.name,
            description=repo.description or "",
            target_audience=analysis.target_audience if analysis else "",
            core_features=[],
            tech_stack=repo.language or "Python",
            monetization_potential=analysis.monetization_potential if analysis else "",
            differentiation_ideas=analysis.differentiation_ideas if analysis and analysis.differentiation_ideas else [],
            problem_solved=analysis.problem_solved if analysis else "",
            project_type=project_type
        )


def quick_generate(
    project_name: str,
    description: str,
    target_audience: str = "开发者",
    core_features: Optional[List[str]] = None,
    project_type: str = "api"
) -> EnhancedGenerationResult:
    """快速生成项目骨架"""
    generator = EnhancedMVPGenerator()
    
    return generator.analyze_and_generate(
        project_name=project_name,
        description=description,
        target_audience=target_audience,
        core_features=core_features or [],
        project_type=project_type
    )


if __name__ == "__main__":
    result = quick_generate(
        project_name="AI Code Reviewer",
        description="An AI-powered code review tool that provides instant feedback",
        target_audience="开发者团队",
        core_features=["代码审查", "AI分析", "自动建议"]
    )
    
    print(f"Generated: {result.project_name}")
    print(f"Prompts used: {list(result.prompts_used.keys())}")
    if result.generated_project:
        print(f"Output: {result.generated_project.output_path}")
