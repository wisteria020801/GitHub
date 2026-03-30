# GitHub 趋势雷达

自动发现 GitHub 热门开源项目，分析其商业价值，并推送到 Telegram。

## 快速开始

### 1. 本地运行

```bash
cd github_radar
pip install -r requirements.txt
python main.py --test    # 测试连接
python main.py --once    # 运行一次
python main.py           # 持续运行
```

### 2. GitHub Actions 部署

在 GitHub 仓库设置中添加以下 Secrets：

| Secret 名称 | 说明 |
|------------|------|
| `GITHUB_TOKEN` | GitHub Personal Access Token |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram 聊天 ID |
| `TELEGRAM_CHATGROUP_ID` | Telegram 频道 ID（可选） |
| `GOOGLE_API_KEY` | Gemini API Key |

工作流会每 4 小时自动运行一次。

## 项目结构

```
github_radar/
├── main.py                 # 主入口
├── config.py               # 配置加载
├── database/               # 数据库模块
├── collectors/             # GitHub 采集器
├── analyzers/              # LLM 分析器
├── scorers/                # 评分器
├── notifiers/              # Telegram 推送器
└── utils/                  # 工具函数
```

## 后续规划

- **Phase 3**: 扩展数据源（Hacker News、Product Hunt）
- **Phase 4**: Web 界面
- **Phase 5**: MVP 骨架生成
