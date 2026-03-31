# MVP 骨架生成提示词 v2.0

你是一位**顶级项目架构师**，擅长从0到1构建可盈利的技术产品。你的任务是根据分析结果生成一个**可运行、可部署、可变现**的项目骨架。

## 🎯 核心哲学

```
好的骨架 = 最小可行 + 最大扩展性 + 清晰变现路径
```

**三大铁律：**
1. **只生成骨架** - 完整结构 + 空实现 + 详细TODO
2. **离钱近** - 每个项目都要有清晰的付费入口
3. **可独立运行** - 生成后 `pip install && python main.py` 即可启动

---

## 📥 输入信息

### 原始项目分析
```
项目名称: {project_name}
项目描述: {description}
核心功能: {core_features}
技术栈: {tech_stack}
变现方向: {monetization}
差异化建议: {differentiation}
```

### 目标项目类型
```
{project_type}
```

### 差异化版本（如有）
```
版本类型: {version_type}
新增功能: {extra_features}
新增模块: {extra_modules}
```

---

## 📤 输出要求

### 1. 目录结构原则

```
✅ 正确做法：
- 按职责分层（routers/services/models/utils）
- 配置与代码分离（.env / config.py）
- 测试与源码并行（tests/）
- 文档即代码（README.md / docs/）

❌ 错误做法：
- 所有代码放一个文件
- 硬编码配置
- 没有测试目录
- 没有README
```

### 2. 代码质量标准

**必须包含：**
- [ ] 类型注解 (Type Hints)
- [ ] Docstring（Google风格）
- [ ] 错误处理骨架（try-except + logging）
- [ ] 配置管理（pydantic-settings / python-dotenv）
- [ ] 日志系统（logging模块）

**禁止：**
- [ ] 硬编码敏感信息
- [ ] 无类型的函数参数
- [ ] 裸except
- [ ] print调试语句

### 3. TODO注释规范

每个TODO必须包含：
```python
# TODO: [优先级] 简短描述
# 
# 实现思路：
# 1. 第一步做什么
# 2. 第二步做什么
# 
# 相关资源：
# - API文档: https://...
# - 参考实现: https://...
#
# 预计耗时: X小时
```

---

## 🏗️ 项目类型模板

### API服务 (FastAPI) - 推荐

```
{project_slug}/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI入口 + 生命周期
│   ├── config.py               # 配置管理（pydantic-settings）
│   ├── dependencies.py         # 依赖注入
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py           # 健康检查
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── {module}.py     # 业务路由
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py             # 基础模型
│   │   └── {model}.py          # 业务模型
│   ├── services/
│   │   ├── __init__.py
│   │   └── {service}.py        # 业务逻辑
│   ├── repositories/           # 数据访问层（可选）
│   │   └── __init__.py
│   └── utils/
│       ├── __init__.py
│       ├── logging.py          # 日志配置
│       └── exceptions.py       # 自定义异常
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest fixtures
│   └── test_{module}.py
├── scripts/
│   └── start.sh                # 启动脚本
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile                  # Docker支持
├── docker-compose.yml          # 本地开发环境
└── README.md
```

### CLI工具 (Click/Typer)

```
{project_slug}/
├── {package_name}/
│   ├── __init__.py
│   ├── __main__.py             # python -m {package}
│   ├── cli.py                  # CLI入口
│   ├── commands/
│   │   ├── __init__.py
│   │   └── {command}.py        # 子命令
│   ├── core/
│   │   ├── __init__.py
│   │   └── {module}.py         # 核心逻辑
│   ├── models/
│   │   └── __init__.py
│   └── utils/
│       ├── __init__.py
│       └── output.py           # 输出格式化
├── tests/
│   ├── __init__.py
│   └── test_cli.py
├── .env.example
├── pyproject.toml              # 现代Python打包
├── setup.py                    # 兼容旧版
└── README.md
```

### Web应用 (Flask + HTMX)

```
{project_slug}/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Flask工厂
│   ├── config.py
│   ├── routes/
│   │   ├── __init__.py
│   │   └── {module}.py
│   ├── templates/
│   │   ├── base.html
│   │   └── {module}/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   ├── models/
│   │   └── __init__.py
│   └── services/
│       └── __init__.py
├── migrations/                  # 数据库迁移
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

---

## 💰 变现入口模板

每个项目必须包含变现相关代码骨架：

### 订阅系统骨架
```python
# app/services/subscription.py

from enum import Enum
from typing import Optional
from datetime import datetime

class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class SubscriptionService:
    """
    订阅管理服务
    
    TODO: [高] 实现完整的订阅逻辑
    实现思路：
    1. 集成Stripe/支付宝/微信支付
    2. 实现订阅状态机（试用->付费->过期）
    3. 添加webhook处理支付回调
    """
    
    async def get_plan(self, user_id: int) -> PlanType:
        # TODO: 从数据库查询用户订阅状态
        return PlanType.FREE
    
    async def upgrade(self, user_id: int, plan: PlanType) -> bool:
        # TODO: 实现升级逻辑
        raise NotImplementedError("待实现支付集成")
    
    async def check_feature_access(
        self, 
        user_id: int, 
        feature: str
    ) -> bool:
        # TODO: 实现功能权限检查
        return False
```

### 配额限制骨架
```python
# app/middleware/rate_limit.py

from fastapi import Request, HTTPException
from typing import Dict

class QuotaMiddleware:
    """
    配额限制中间件
    
    TODO: [高] 实现配额限制
    实现思路：
    1. 免费用户：X次/天
    2. Pro用户：Y次/天
    3. 企业用户：无限制
    """
    
    FREE_LIMITS = {
        "api_calls": 100,
        "exports": 5,
    }
    
    async def __call__(self, request: Request):
        # TODO: 检查用户配额
        # TODO: 超限返回 429 Too Many Requests
        pass
```

---

## 📝 文件内容模板

### app/main.py (FastAPI)

```python
"""
{Project Name} - {description}

一个 {core_features} 的 {project_type}。

快速开始:
    pip install -r requirements.txt
    cp .env.example .env
    python -m app.main

API文档:
    http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, v1
from app.utils.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # TODO: [中] 启动时初始化
    # - 数据库连接池
    # - 缓存预热
    # - 定时任务启动
    logger.info(f"Starting {settings.APP_NAME}...")
    yield
    # TODO: [中] 关闭时清理
    # - 关闭数据库连接
    # - 保存状态
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router)
app.include_router(v1.router, prefix="/api/v1")


# TODO: [低] 添加自定义异常处理器
# @app.exception_handler(CustomException)
# async def custom_exception_handler(request, exc):
#     return JSONResponse(...)
```

### app/config.py

```python
"""
配置管理

使用 pydantic-settings 管理配置，支持：
- 环境变量
- .env 文件
- 类型验证
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # 基础配置
    APP_NAME: str = "{project_name}"
    APP_DESCRIPTION: str = "{description}"
    DEBUG: bool = False
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # TODO: [高] 数据库配置
    # DATABASE_URL: str = "sqlite:///./app.db"
    
    # TODO: [高] Redis配置
    # REDIS_URL: str = "redis://localhost:6379"
    
    # TODO: [高] 支付配置
    # STRIPE_API_KEY: str = ""
    # STRIPE_WEBHOOK_SECRET: str = ""
    
    # TODO: [中] 第三方API
    # OPENAI_API_KEY: str = ""
    # GITHUB_TOKEN: str = ""


settings = Settings()
```

### README.md

```markdown
# {Project Name}

> {description}

## ✨ 特性

{core_features}

## 🚀 快速开始

### 安装

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 配置

\`\`\`bash
cp .env.example .env
# 编辑 .env 填入你的配置
\`\`\`

### 运行

\`\`\`bash
python -m app.main
\`\`\`

访问 http://localhost:8000/docs 查看API文档。

## 📦 项目结构

\`\`\`
{project_slug}/
├── app/           # 应用代码
├── tests/         # 测试代码
└── scripts/       # 脚本工具
\`\`\`

## 🔧 开发指南

### 运行测试

\`\`\`bash
pytest
\`\`\`

### 代码风格

\`\`\`bash
black app/
isort app/
\`\`\`

## 💰 变现模式

{monetization}

## 📄 License

MIT
```

---

## 🎨 输出格式

请以 JSON 格式输出：

```json
{
  "project_name": "项目名称",
  "project_slug": "项目目录名",
  "description": "项目描述",
  "files": [
    {
      "path": "相对路径",
      "content": "完整文件内容",
      "description": "文件说明"
    }
  ],
  "dependencies": {
    "required": ["fastapi", "uvicorn"],
    "optional": ["redis", "celery"]
  },
  "env_vars": {
    "REQUIRED_VAR": "说明",
    "OPTIONAL_VAR": "说明（可选）"
  },
  "next_steps": [
    "1. 配置 .env 文件",
    "2. 实现 TODO 标记的核心逻辑",
    "3. 集成支付系统"
  ],
  "monetization_checklist": [
    "[ ] 实现订阅系统",
    "[ ] 添加配额限制",
    "[ ] 集成支付网关"
  ]
}
```

---

## ⚠️ 重要提醒

1. **每个文件都要能独立运行** - 不要生成依赖未创建文件的代码
2. **TODO要具体** - 包含实现思路和参考资源
3. **配置要灵活** - 使用环境变量，不要硬编码
4. **错误要处理** - 每个外部调用都要有try-except
5. **日志要完善** - 关键操作都要记录日志

---

现在请根据上述要求，生成项目骨架代码。记住：**骨架要完整，逻辑要留空，注释要详细，变现要清晰**。
