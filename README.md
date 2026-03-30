# GitHub 趋势雷达

自动发现 GitHub 热门开源项目，分析其商业价值，并推送到 Telegram。

## 功能特性

- 🔍 **多数据源采集**: GitHub、Hacker News、Product Hunt
- 🤖 **AI 智能分析**: 使用 Gemini 分析项目商业价值
- 📊 **智能评分**: 100分制评分系统，筛选高价值项目
- 📱 **Telegram 推送**: 自动推送高分项目到 Telegram
- ⏰ **定时任务**: 支持 GitHub Actions 自动运行

## 快速开始

### 1. 本地运行

```bash
cd github_radar
pip install -r requirements.txt
python main.py --test    # 测试连接
python main.py --once    # 运行一次（多数据源）
python main.py --once --single-source  # 仅 GitHub 数据源
python main.py           # 持续运行
```

### 2. GitHub Actions 部署

在 GitHub 仓库设置中添加以下 Secrets：

| Secret 名称 | 说明 |
|------------|------|
| `TOKEN_GITHUB` | GitHub Personal Access Token |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram 聊天 ID |
| `TELEGRAM_CHATGROUP_ID` | Telegram 频道 ID（可选） |
| `GOOGLE_API_KEY` | Gemini API Key |
| `PRODUCTHUNT_API_TOKEN` | Product Hunt API Token（可选） |

工作流会每 4 小时自动运行一次。

## 项目结构

```
github_radar/
├── main.py                 # 主入口
├── config.py               # 配置加载
├── database/               # 数据库模块
├── collectors/             # 数据采集器
│   ├── github_collector.py # GitHub 采集
│   ├── hn_collector.py     # Hacker News 采集
│   ├── ph_collector.py     # Product Hunt 采集
│   └── multi_source.py     # 多源统一管理
├── analyzers/              # LLM 分析器
├── scorers/                # 评分器
├── notifiers/              # Telegram 推送器
└── utils/                  # 工具函数
```

## 数据源说明

| 数据源 | 采集内容 | API 要求 |
|--------|----------|----------|
| GitHub | 7天内创建、stars>50 的热门项目 | 需要 Token |
| Hacker News | 24小时内 score>100 的热门故事 | 免费 |
| Product Hunt | 当日热门产品 | 可选 Token |

## 后续规划

- **Phase 4**: Web 界面
- **Phase 5**: MVP 骨架生成
