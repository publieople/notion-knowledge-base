# 📚 Notion Knowledge Base

自动同步来自 Notion 的知识库内容。

## 目录结构

```
articles/          ← 原创文章 & 工具评测 (Notion 子页面)
curations/
├── tools/         ← 工具策展数据库条目
└── communities/   ← 社区数据库条目
scripts/
  sync.py          ← 同步脚本
_mapping.json      ← Notion page_id ↔ 文件路径映射
_sync_state.json   ← 同步状态跟踪 (文件哈希)
```

## 文件格式

每篇文章是一个 Markdown 文件，头部是 YAML frontmatter：

```yaml
---
title: 优雅的文件管理
source: article          # 类型: article / tool / community
notion_id: b4266ad7...   # Notion Page ID (用于双向同步)
tags:
  - 电脑基础
  - 文件管理
last_edited_time: 2026-05-04
---
```

工具和社区条目保留了 Notion 数据库属性（标签、网址、用途等）。

## 同步

每周自动同步（双向）：
- Notion → GitHub: 提取内容变化
- GitHub → Notion: 检测文件修改并回写

手动同步：
```bash
python3 scripts/sync.py              # Notion → GitHub
python3 scripts/sync.py --reverse    # GitHub → Notion
```

## 仓库信息

- 原始内容: [通识分享企划] Notion 工作区
- 发布平台: [Publieople's Blog](https://publieople.com)
- 作者: [人民公仆 / Publieople](https://github.com/publieople)
