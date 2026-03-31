"""
差异化版本生成器

根据分析结果生成多个差异化版本的项目骨架
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import re

from utils.logger import get_logger
from generators.mvp_generator import MVPGenerator, GeneratedProject

logger = get_logger(__name__)


DIFFERENTIATION_TEMPLATES = {
    "中文版": {
        "suffix": "-cn",
        "features": ["中文文档", "本地化支持", "中文社区"],
        "modules": ["i18n", "translate"],
        "description_template": "{name} - 中文本地化版本，提供完整的中文文档和本地化支持"
    },
    "Telegram推送版": {
        "suffix": "-telegram",
        "features": ["Telegram Bot集成", "实时推送", "自定义订阅"],
        "modules": ["notifier", "telegram"],
        "description_template": "{name} - 集成Telegram推送，支持实时通知和自定义订阅"
    },
    "付费订阅版": {
        "suffix": "-pro",
        "features": ["订阅系统", "支付集成", "高级功能", "用户管理"],
        "modules": ["payment", "subscription", "auth"],
        "description_template": "{name} - 付费订阅版本，支持多种支付方式和会员体系"
    },
    "企业版": {
        "suffix": "-enterprise",
        "features": ["SSO登录", "权限管理", "审计日志", "私有部署"],
        "modules": ["auth", "audit", "rbac"],
        "description_template": "{name} - 企业级版本，支持SSO、权限管理和私有部署"
    },
    "API服务版": {
        "suffix": "-api",
        "features": ["RESTful API", "API文档", "Rate Limiting", "Webhook"],
        "modules": ["api", "webhook", "ratelimit"],
        "description_template": "{name} - API服务版本，提供完整的RESTful API和Webhook支持"
    },
    "CLI工具版": {
        "suffix": "-cli",
        "features": ["命令行工具", "批量操作", "脚本支持"],
        "modules": ["cli", "batch"],
        "description_template": "{name} - 命令行工具版本，支持批量操作和自动化脚本"
    },
    "移动端版": {
        "suffix": "-mobile",
        "features": ["移动端适配", "PWA支持", "离线使用"],
        "modules": ["mobile", "pwa"],
        "description_template": "{name} - 移动端版本，支持PWA和离线使用"
    },
    "自动化增强版": {
        "suffix": "-auto",
        "features": ["自动化工作流", "定时任务", "智能调度"],
        "modules": ["automation", "scheduler"],
        "description_template": "{name} - 自动化增强版本，支持工作流编排和智能调度"
    }
}


@dataclass
class DifferentiatedVersion:
    version_name: str
    suffix: str
    features: List[str]
    modules: List[str]
    description: str
    project: GeneratedProject


@dataclass
class MultiVersionResult:
    original_name: str
    versions: List[DifferentiatedVersion]
    generated_at: datetime
    output_dir: str


class DifferentiatedGenerator:
    def __init__(self, output_dir: Optional[str] = None):
        self.base_generator = MVPGenerator()
        if output_dir:
            self.base_generator.OUTPUT_DIR = Path(output_dir)
    
    def generate_versions(
        self,
        project_name: str,
        analysis_result: Dict[str, Any],
        selected_versions: Optional[List[str]] = None,
        base_type: str = "api"
    ) -> MultiVersionResult:
        differentiation_ideas = analysis_result.get("differentiation_ideas", [])
        
        if not selected_versions:
            selected_versions = self._select_versions_from_ideas(differentiation_ideas)
        
        versions = []
        
        for version_name in selected_versions:
            if version_name not in DIFFERENTIATION_TEMPLATES:
                logger.warning(f"Unknown version type: {version_name}, skipping")
                continue
            
            template = DIFFERENTIATION_TEMPLATES[version_name]
            
            version_project = self._generate_single_version(
                project_name=project_name,
                version_name=version_name,
                template=template,
                analysis_result=analysis_result,
                base_type=base_type
            )
            
            versions.append(DifferentiatedVersion(
                version_name=version_name,
                suffix=template["suffix"],
                features=template["features"],
                modules=template["modules"],
                description=template["description_template"].format(name=project_name),
                project=version_project
            ))
        
        result = MultiVersionResult(
            original_name=project_name,
            versions=versions,
            generated_at=datetime.now(),
            output_dir=str(self.base_generator.OUTPUT_DIR)
        )
        
        self._save_multi_version_meta(result)
        
        logger.info(f"Generated {len(versions)} differentiated versions for {project_name}")
        
        return result
    
    def _select_versions_from_ideas(self, ideas: List[str]) -> List[str]:
        selected = []
        ideas_text = " ".join(ideas).lower() if ideas else ""
        
        version_keywords = {
            "中文版": ["中文", "本地化", "国内", "china", "chinese"],
            "Telegram推送版": ["telegram", "推送", "通知", "notify", "push"],
            "付费订阅版": ["付费", "订阅", "saas", "subscription", "payment"],
            "企业版": ["企业", "enterprise", "私有", "private"],
            "API服务版": ["api", "rest", "接口"],
            "CLI工具版": ["cli", "命令行", "terminal"],
            "移动端版": ["移动", "mobile", "app", "pwa"],
            "自动化增强版": ["自动化", "automation", "工作流", "workflow"]
        }
        
        for version, keywords in version_keywords.items():
            if any(kw in ideas_text for kw in keywords):
                selected.append(version)
        
        if not selected:
            selected = ["中文版", "Telegram推送版", "付费订阅版"]
        
        return selected[:4]
    
    def _generate_single_version(
        self,
        project_name: str,
        version_name: str,
        template: Dict[str, Any],
        analysis_result: Dict[str, Any],
        base_type: str
    ) -> GeneratedProject:
        version_name_formatted = f"{project_name}{template['suffix']}"
        
        enhanced_analysis = analysis_result.copy()
        enhanced_analysis["summary"] = template["description_template"].format(name=project_name)
        enhanced_analysis["features"] = template["features"]
        enhanced_analysis["modules"] = template["modules"]
        
        project = self.base_generator.generate(
            project_name=version_name_formatted,
            project_type=base_type,
            analysis_result=enhanced_analysis,
            custom_vars={
                "VERSION_TYPE": version_name,
                "EXTRA_FEATURES": "\n".join(f"- {f}" for f in template["features"]),
                "EXTRA_MODULES": ", ".join(template["modules"])
            }
        )
        
        self._add_version_specific_files(project, template, analysis_result)
        
        return project
    
    def _add_version_specific_files(
        self,
        project: GeneratedProject,
        template: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> None:
        output_path = Path(project.output_path)
        
        for module in template["modules"]:
            module_dir = output_path / "app" / "modules" / module
            module_dir.mkdir(parents=True, exist_ok=True)
            
            init_file = module_dir / "__init__.py"
            if not init_file.exists():
                init_file.write_text(f'"""{module} module"""\n', encoding="utf-8")
            
            module_file = module_dir / f"{module}.py"
            if not module_file.exists():
                module_code = self._generate_module_code(module, template, analysis_result)
                module_file.write_text(module_code, encoding="utf-8")
        
        project.files.append({
            "path": f"app/modules/{template['modules'][0]}/{template['modules'][0]}.py",
            "content": "Generated module",
            "description": f"Version-specific module for {template['suffix']}"
        })
    
    def _generate_module_code(
        self,
        module: str,
        template: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> str:
        module_templates = {
            "i18n": '''"""
国际化模块

支持多语言翻译和本地化
"""
from typing import Dict, Optional
import json
from pathlib import Path


class I18nManager:
    """国际化管理器"""
    
    def __init__(self, locale: str = "zh_CN"):
        self.locale = locale
        self.translations: Dict[str, str] = {}
        self._load_translations()
    
    def _load_translations(self):
        """加载翻译文件"""
        # TODO: 实现翻译文件加载
        pass
    
    def t(self, key: str, **kwargs) -> str:
        """翻译文本"""
        # TODO: 实现翻译逻辑
        return key
    
    def set_locale(self, locale: str):
        """设置语言"""
        self.locale = locale
        self._load_translations()


i18n = I18nManager()
''',
            "telegram": '''"""
Telegram 推送模块

集成 Telegram Bot API 实现消息推送
"""
import requests
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str


class TelegramNotifier:
    """Telegram 通知器"""
    
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.api_base = f"https://api.telegram.org/bot{config.bot_token}"
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """发送消息"""
        # TODO: 实现消息发送
        return True
    
    async def send_photo(self, photo_url: str, caption: str = "") -> bool:
        """发送图片"""
        # TODO: 实现图片发送
        return True
''',
            "payment": '''"""
支付模块

支持多种支付方式
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class PaymentProvider(Enum):
    STRIPE = "stripe"
    ALIPAY = "alipay"
    WECHAT = "wechat"


@dataclass
class PaymentResult:
    success: bool
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None


class PaymentService:
    """支付服务"""
    
    def __init__(self, provider: PaymentProvider):
        self.provider = provider
    
    async def create_payment(
        self,
        amount: float,
        currency: str = "USD",
        **kwargs
    ) -> PaymentResult:
        """创建支付"""
        # TODO: 实现支付创建
        return PaymentResult(success=False, error_message="Not implemented")
    
    async def verify_payment(self, transaction_id: str) -> bool:
        """验证支付"""
        # TODO: 实现支付验证
        return False
''',
            "auth": '''"""
认证模块

支持多种认证方式
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import jwt


@dataclass
class User:
    id: int
    username: str
    email: str
    role: str = "user"


class AuthService:
    """认证服务"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    def create_token(self, user: User, expires_hours: int = 24) -> str:
        """创建 JWT Token"""
        # TODO: 实现 Token 创建
        return ""
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证 Token"""
        # TODO: 实现 Token 验证
        return None
    
    async def login(self, username: str, password: str) -> Optional[User]:
        """用户登录"""
        # TODO: 实现登录逻辑
        return None
''',
            "automation": '''"""
自动化模块

支持工作流自动化和定时任务
"""
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import asyncio


@dataclass
class Task:
    id: str
    name: str
    schedule: str  # cron expression
    handler: str
    enabled: bool = True
    last_run: Optional[datetime] = None


class AutomationEngine:
    """自动化引擎"""
    
    def __init__(self):
        self.tasks: List[Task] = []
        self.handlers: Dict[str, Callable] = {}
    
    def register_task(self, task: Task):
        """注册任务"""
        # TODO: 实现任务注册
        pass
    
    async def run_task(self, task_id: str):
        """执行任务"""
        # TODO: 实现任务执行
        pass
    
    async def start(self):
        """启动自动化引擎"""
        # TODO: 实现调度循环
        pass
'''
        }
        
        return module_templates.get(module, f'"""{module} module"""\n# TODO: Implement {module} module\n')
    
    def _save_multi_version_meta(self, result: MultiVersionResult) -> None:
        meta = {
            "original_name": result.original_name,
            "versions": [
                {
                    "name": v.version_name,
                    "suffix": v.suffix,
                    "features": v.features,
                    "modules": v.modules,
                    "description": v.description,
                    "output_path": v.project.output_path
                }
                for v in result.versions
            ],
            "generated_at": result.generated_at.isoformat(),
            "output_dir": result.output_dir
        }
        
        meta_file = Path(result.output_dir) / self.base_generator._create_slug(result.original_name) / ".multi_version.json"
        meta_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)


def generate_differentiated_mvps(
    repo_id: int,
    selected_versions: Optional[List[str]] = None
) -> Optional[MultiVersionResult]:
    from database.db_manager import DatabaseManager
    
    db = DatabaseManager()
    
    repo = db.get_repository_by_id(repo_id)
    if not repo:
        logger.error(f"Repository not found: {repo_id}")
        return None
    
    analysis = db.get_analysis_by_repo_id(repo_id)
    
    analysis_result = {
        "summary": repo.description or "",
        "business_potential": analysis.target_audience if analysis else "",
        "differentiation_ideas": analysis.differentiation_ideas if analysis and analysis.differentiation_ideas else [],
        "monetization": analysis.monetization_potential if analysis else "",
    }
    
    generator = DifferentiatedGenerator()
    
    return generator.generate_versions(
        project_name=repo.name,
        analysis_result=analysis_result,
        selected_versions=selected_versions
    )


if __name__ == "__main__":
    result = generate_differentiated_mvps(repo_id=1)
    if result:
        print(f"Generated {len(result.versions)} versions:")
        for v in result.versions:
            print(f"  - {v.version_name}: {v.project.output_path}")
