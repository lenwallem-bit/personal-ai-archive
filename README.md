# AI-READONLY: 个人 AI 档案入口

这个仓库使用普通 UTF-8 Markdown 保存可公开的个人档案，让不同 AI 和设备读取同一份经过确认的信息。仓库地址为 [lenwallem-bit/personal-ai-archive](https://github.com/lenwallem-bit/personal-ai-archive)。实际部署和验证状态见交付报告。

初始文件是模板。`{{占位符}}` 表示尚未填写，`template` 和 `unknown` 表示没有足够信息；AI 不得将它们当成事实，也不得从其他聊天自动补入私人资料。

## 从这里开始

1. 阅读 [快速接入指南](QUICKSTART.md)，复制其中的通用提示词。
2. AI 依次读取 [AGENTS.md](AGENTS.md)、[archive-manifest.json](archive-manifest.json)、[个人身份](identity/profile.md) 和 [工作偏好](workflow/preferences.md)，再按任务需要读取其余文件。
3. 各平台的读取、写入和自动同步边界见 [ai-integration.md](ai-integration.md)。能访问仓库不等于平台会持续同步。

## 目录说明

| 目录 | 保存内容 | 常用入口 | 更新方式 |
| --- | --- | --- | --- |
| `identity/` | 身份、职业、核心标签、人生目标、公开边界 | [profile.md](identity/profile.md) | 用户明确授权后提交 PR |
| `workflow/` | 工作习惯、工具、沟通方式和优先级 | [preferences.md](workflow/preferences.md) | 确认变化后提交 PR |
| `memory/` | 经历复盘、决策和已确认的偏好 | [README.md](memory/README.md) | 自动候选只追加到 `entries/`，经检查后合并 |
| `skills/` | 已掌握技能、学习计划、待提升能力 | [competencies.md](skills/competencies.md) | 依据实际证据提交 PR |
| `archive/` | 历史项目、文档索引和已完成任务 | [projects.md](archive/projects.md) | 归档核实后的公开摘要 |

## 自动更新约定

任务完成后，支持写入的适配器可以提炼可复用经验。内容必须适合公开、来源可核实、未重复且未与现有记忆冲突。自动写入范围限定为 `memory/entries/<event_id>.md` 的新文件；身份、规则、工具配置和已有记录不允许由自动记录器覆盖。

写入先进入独立分支和 PR，检查通过后才进入主分支。无法确认可公开的内容留在执行环境的私有待处理区；仅有读取能力的平台应返回候选内容，不能声称已保存。

## 版本与恢复

Git 提交记录保存变更历史。恢复历史内容时创建新的恢复 PR，保留后续审计记录，不使用强制推送重写主分支。具体恢复入口和实际启用的保护项以交付报告及 [安全与版本规则](SECURITY.md) 为准。

`AI-READONLY` 和 `AI-WRITABLE` 是供 AI 理解的约定；真正的写入限制由适配器、仓库权限、检查和分支保护共同落实。

本仓库公开。不要提交密码、令牌、家庭住址、私密健康信息、未经授权的他人资料或原始聊天记录；删除文件不会使已公开的历史副本消失。
