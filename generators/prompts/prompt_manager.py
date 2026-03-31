"""
提示词管理器

统一管理所有生成器提示词，支持变量替换和模板渲染
"""
from pathlib import Path
from typing import Dict, Any, Optional
import re

from utils.logger import get_logger

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).parent


class PromptManager:
    """提示词管理器"""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        self._cache: Dict[str, str] = {}
    
    def load_prompt(self, prompt_name: str) -> str:
        """加载提示词文件"""
        if prompt_name in self._cache:
            return self._cache[prompt_name]
        
        prompt_file = self.prompts_dir / f"{prompt_name}.md"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        self._cache[prompt_name] = content
        
        logger.debug(f"Loaded prompt: {prompt_name}")
        
        return content
    
    def render_prompt(
        self, 
        prompt_name: str, 
        variables: Dict[str, Any]
    ) -> str:
        """渲染提示词，替换变量"""
        template = self.load_prompt(prompt_name)
        
        rendered = template
        
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            rendered = rendered.replace(placeholder, str(value) if value else "")
        
        remaining_vars = re.findall(r'\{(\w+)\}', rendered)
        if remaining_vars:
            logger.warning(f"Unfilled variables in prompt: {remaining_vars}")
        
        return rendered
    
    def get_code_generation_prompt(
        self,
        project_name: str,
        description: str,
        core_features: str,
        tech_stack: str,
        monetization: str,
        differentiation: str,
        project_type: str = "api",
        version_type: Optional[str] = None,
        extra_features: Optional[str] = None,
        extra_modules: Optional[str] = None
    ) -> str:
        """获取代码生成提示词"""
        variables = {
            "project_name": project_name,
            "description": description,
            "core_features": core_features,
            "tech_stack": tech_stack,
            "monetization": monetization,
            "differentiation": differentiation,
            "project_type": project_type,
            "project_slug": self._create_slug(project_name),
            "version_type": version_type or "",
            "extra_features": extra_features or "",
            "extra_modules": extra_modules or ""
        }
        
        return self.render_prompt("generate_code", variables)
    
    def get_differentiation_prompt(
        self,
        project_name: str,
        description: str,
        core_features: str,
        target_audience: str,
        competitors: str = "",
        tech_stack: str = ""
    ) -> str:
        """获取差异化分析提示词"""
        variables = {
            "project_name": project_name,
            "description": description,
            "core_features": core_features,
            "target_audience": target_audience,
            "competitors": competitors,
            "tech_stack": tech_stack
        }
        
        return self.render_prompt("differentiation", variables)
    
    def get_tech_stack_prompt(
        self,
        project_name: str,
        project_type: str,
        core_features: str,
        performance_requirements: str = "中等",
        team_size: str = "1-3人",
        expected_users: str = "1000-10000"
    ) -> str:
        """获取技术栈选择提示词"""
        variables = {
            "project_name": project_name,
            "project_type": project_type,
            "core_features": core_features,
            "performance_requirements": performance_requirements,
            "team_size": team_size,
            "expected_users": expected_users
        }
        
        return self.render_prompt("tech_stack", variables)
    
    def get_monetization_prompt(
        self,
        project_name: str,
        description: str,
        target_audience: str,
        core_features: str,
        problem_solved: str,
        expected_users: str = "1000-10000"
    ) -> str:
        """获取变现策略提示词"""
        variables = {
            "project_name": project_name,
            "description": description,
            "target_audience": target_audience,
            "core_features": core_features,
            "problem_solved": problem_solved,
            "expected_users": expected_users
        }
        
        return self.render_prompt("monetization", variables)
    
    def get_full_analysis_prompt(
        self,
        project_name: str,
        description: str,
        core_features: str,
        target_audience: str,
        tech_stack: str = "",
        competitors: str = "",
        problem_solved: str = ""
    ) -> Dict[str, str]:
        """获取完整分析提示词集合"""
        return {
            "differentiation": self.get_differentiation_prompt(
                project_name=project_name,
                description=description,
                core_features=core_features,
                target_audience=target_audience,
                competitors=competitors,
                tech_stack=tech_stack
            ),
            "tech_stack": self.get_tech_stack_prompt(
                project_name=project_name,
                project_type="API服务",
                core_features=core_features
            ),
            "monetization": self.get_monetization_prompt(
                project_name=project_name,
                description=description,
                target_audience=target_audience,
                core_features=core_features,
                problem_solved=problem_solved
            )
        }
    
    def _create_slug(self, name: str) -> str:
        """创建项目slug"""
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        return slug
    
    def list_available_prompts(self) -> list:
        """列出所有可用的提示词"""
        prompts = []
        for f in self.prompts_dir.glob("*.md"):
            prompts.append(f.stem)
        return sorted(prompts)
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        logger.debug("Prompt cache cleared")


prompt_manager = PromptManager()


if __name__ == "__main__":
    pm = PromptManager()
    
    print("Available prompts:", pm.list_available_prompts())
    
    code_prompt = pm.get_code_generation_prompt(
        project_name="My Awesome API",
        description="A powerful API service",
        core_features="Data processing, Analytics, Reporting",
        tech_stack="Python, FastAPI, PostgreSQL",
        monetization="Freemium model",
        differentiation="Chinese version, Telegram integration"
    )
    
    print("\n" + "="*50)
    print("Code Generation Prompt (first 500 chars):")
    print("="*50)
    print(code_prompt[:500] + "...")
