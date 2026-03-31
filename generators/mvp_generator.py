"""
MVP 骨架生成器

根据分析结果生成项目骨架代码
"""
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GeneratedProject:
    name: str
    slug: str
    project_type: str
    description: str
    files: List[Dict[str, str]]
    output_path: str
    created_at: datetime


class MVPGenerator:
    """MVP 骨架生成器"""
    
    TEMPLATE_DIR = Path(__file__).parent / "templates"
    OUTPUT_DIR = Path(__file__).parent.parent / "generated_mvps"
    
    PROJECT_TYPES = {
        "api": "api_service/fastapi",
        "cli": "cli_tool/python",
        "fastapi": "api_service/fastapi",
        "cli_tool": "cli_tool/python",
        "web": "web_frontend/react",
        "react": "web_frontend/react",
        "web_frontend": "web_frontend/react",
        "chrome": "chrome_extension/basic",
        "extension": "chrome_extension/basic",
        "chrome_extension": "chrome_extension/basic",
        "discord": "discord_bot/python",
        "discord_bot": "discord_bot/python",
        "bot": "discord_bot/python",
    }
    
    def __init__(self):
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        project_name: str,
        project_type: str,
        analysis_result: Dict[str, Any],
        custom_vars: Optional[Dict[str, str]] = None
    ) -> GeneratedProject:
        """生成项目骨架"""
        
        project_type_key = project_type.lower().replace("-", "_").replace(" ", "_")
        template_path = self.TEMPLATE_DIR / self.PROJECT_TYPES.get(project_type_key, "api_service/fastapi")
        
        if not template_path.exists():
            raise ValueError(f"Template not found for project type: {project_type}")
        
        template_file = template_path / "template.json"
        if not template_file.exists():
            raise FileNotFoundError(f"Template file not found: {template_file}")
        
        with open(template_file, "r", encoding="utf-8") as f:
            template = json.load(f)
        
        slug = self._create_slug(project_name)
        package_name = slug.replace("-", "_")
        
        variables = {
            "PROJECT_NAME": project_name,
            "PROJECT_SLUG": slug,
            "PROJECT_DESCRIPTION": analysis_result.get("summary", ""),
            "CORE_FEATURES": self._extract_features(analysis_result),
            "TECH_STACK": analysis_result.get("tech_stack", "Python"),
            "MONETIZATION": analysis_result.get("monetization", "待规划"),
            "DIFFERENTIATION": analysis_result.get("differentiation", "待规划"),
            "PACKAGE_NAME": package_name,
        }
        
        if custom_vars:
            variables.update(custom_vars)
        
        files = []
        for file_template in template["files"]:
            content = self._render_template(file_template["content"], variables)
            path = self._render_template(file_template["path"], variables)
            
            files.append({
                "path": path,
                "content": content,
                "description": file_template.get("description", "")
            })
        
        output_path = self.OUTPUT_DIR / slug
        self._write_files(output_path, files)
        
        project = GeneratedProject(
            name=project_name,
            slug=slug,
            project_type=project_type,
            description=variables["PROJECT_DESCRIPTION"],
            files=files,
            output_path=str(output_path),
            created_at=datetime.now()
        )
        
        logger.info(f"Generated MVP project: {project_name} at {output_path}")
        
        return project
    
    def _create_slug(self, name: str) -> str:
        """创建项目 slug"""
        slug = name.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug.strip("-")
    
    def _render_template(self, template: str, variables: Dict[str, str]) -> str:
        """渲染模板"""
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
    
    def _extract_features(self, analysis: Dict[str, Any]) -> str:
        """提取核心功能"""
        features = []
        
        if "business_potential" in analysis:
            features.append(f"- 商业潜力: {analysis['business_potential']}")
        
        if "differentiation" in analysis:
            features.append(f"- 差异化方向: {analysis['differentiation']}")
        
        if "monetization" in analysis:
            features.append(f"- 变现方向: {analysis['monetization']}")
        
        return "\n".join(features) if features else "待分析"
    
    def _write_files(self, output_path: Path, files: List[Dict[str, str]]) -> None:
        """写入文件"""
        for file_info in files:
            file_path = output_path / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_info["content"])
            
            logger.debug(f"Created file: {file_path}")
    
    def list_generated_projects(self) -> List[Dict[str, Any]]:
        """列出已生成的项目"""
        projects = []
        
        for project_dir in self.OUTPUT_DIR.iterdir():
            if project_dir.is_dir():
                meta_file = project_dir / ".meta.json"
                if meta_file.exists():
                    with open(meta_file, "r", encoding="utf-8") as f:
                        projects.append(json.load(f))
                else:
                    projects.append({
                        "name": project_dir.name,
                        "slug": project_dir.name,
                        "output_path": str(project_dir),
                        "created_at": datetime.fromtimestamp(project_dir.stat().st_ctime).isoformat()
                    })
        
        return sorted(projects, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def save_project_meta(self, project: GeneratedProject) -> None:
        """保存项目元数据"""
        meta_file = Path(project.output_path) / ".meta.json"
        
        meta = {
            "name": project.name,
            "slug": project.slug,
            "project_type": project.project_type,
            "description": project.description,
            "output_path": project.output_path,
            "created_at": project.created_at.isoformat(),
            "file_count": len(project.files)
        }
        
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)


def generate_mvp_from_repo(
    repo_id: int,
    project_type: str = "api",
    output_dir: Optional[str] = None
) -> Optional[GeneratedProject]:
    """从仓库生成 MVP
    
    Args:
        repo_id: 仓库 ID
        project_type: 项目类型 (api/cli)
        output_dir: 输出目录
    
    Returns:
        GeneratedProject 或 None
    """
    from database.db_manager import DatabaseManager
    
    db = DatabaseManager()
    
    repo = db.get_repository_by_id(repo_id)
    if not repo:
        logger.error(f"Repository not found: {repo_id}")
        return None
    
    analysis = db.get_analysis_by_repo_id(repo_id)
    if not analysis:
        logger.warning(f"No analysis result for repo {repo_id}, using basic info")
        analysis = {
            "summary": repo.description or "",
            "business_potential": "",
            "differentiation": "",
            "monetization": ""
        }
    
    generator = MVPGenerator()
    if output_dir:
        generator.OUTPUT_DIR = Path(output_dir)
    
    project = generator.generate(
        project_name=repo.name,
        project_type=project_type,
        analysis_result={
            "summary": repo.description or "",
            "business_potential": analysis.target_audience if analysis else "",
            "differentiation": "\n".join(analysis.differentiation_ideas) if analysis and analysis.differentiation_ideas else "",
            "monetization": analysis.monetization_potential if analysis else "",
        }
    )
    
    generator.save_project_meta(project)
    
    return project
