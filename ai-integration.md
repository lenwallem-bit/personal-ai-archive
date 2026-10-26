# AI-READONLY: 跨 AI 接入配置与真实能力边界

配置版本：1.0。平台资料核对日期：2026-10-26。仓库：`lenwallem-bit/personal-ai-archive`，权威分支：`main`。

## 通用接入协议

本仓库用 UTF-8 Markdown 保存档案，用 GitHub API 读取，用独立分支和 PR 写回。任何能够读取 HTTPS 或调用本地工具的 AI 都可以使用同一套内容；仓库不会自动替代平台各自的内置记忆。

| 环节 | 必须执行的动作 | 成功证据 |
| --- | --- | --- |
| 任务开始 | 先解析 `main` 的提交 SHA，再按该 SHA 读取 `AGENTS.md`、`archive-manifest.json`、身份和工作偏好，最后读相关记忆 | 固定提交 SHA、文件路径和 SHA-256 |
| 任务完成 | 提炼确有长期价值且允许公开的经验、偏好、决策；保留来源与适用范围 | 合规事件 JSON，不能包含原始聊天 |
| 自动写回 | 只新增 `memory/entries/<event_id>.md`，创建分支和 PR，通过校验再合并 | PR URL、检查结果、合并 SHA |
| 冲突或断网 | 保留本地候选，使用原事件 ID 重试；同 ID 不同内容必须停止 | 待处理状态及具体原因 |
| 跨设备复用 | 下一台设备重新获取同一仓库的最新固定版本 | 与 GitHub 一致的提交 SHA |

身份、目标、核心工作规则及已有记忆的删改需要具体授权。公开资格不明确的候选留在设备的私有待处理区，不能用本仓库的 Issue、PR 草稿或分支暂存，因为这些内容同样公开。

## GitHub REST API

公共读取不必配置令牌，但匿名接口有访问频率限制。写操作使用宿主中已获授权的 GitHub 身份。不得把令牌放入 Markdown、URL、提示词或仓库配置。

```http
GET https://api.github.com/repos/lenwallem-bit/personal-ai-archive/commits/main
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
```

获取返回的完整 `sha` 后，所有本次读取都固定到该值：

```http
GET https://api.github.com/repos/lenwallem-bit/personal-ai-archive/contents/identity/profile.md?ref={{完整提交SHA}}
Accept: application/vnd.github.raw+json
```

读写脚本通过 Git Data API 把单次变更写成一个提交，不逐个覆盖主分支文件。直接使用 Contents API 更新已有文档的客户端必须携带当前 blob `sha`，遇到冲突重新读取，不能盲目覆盖。

## 平台适配表

| 平台 | 实际读取方式 | 写回与自动更新 | 本仓库配置不代表什么 |
| --- | --- | --- | --- |
| ChatGPT | 已连接 GitHub 工具按需读取；支持工具的会话也可调用本地读写脚本 | 按本会话实际暴露的写工具、Codex 或本机适配器提交 PR | 常规 GitHub app 文档描述的只读入口，不等于每个会话都有写权限；接入不会生成自动同步索引 |
| Gemini 网页版 | 在电脑端通过 Import code 导入 GitHub 仓库 | 网页导入本身不能写回；需要另外的工具宿主 | 导入后是快照，仓库更新不会自动反映；仅粘贴 URL 不能视为已读 |
| Gemini API | 宿主通过 function calling 调用 GitHub API 或本仓库脚本 | 宿主实现任务前后触发并实际执行工具 | 模型输出函数调用参数，不等于 HTTP 请求已经执行 |
| Claude | GitHub 集成选择文件，或通过 Claude Code / MCP 读取 | 原生项目资料用 Sync 刷新；写回需可写执行环境 | 不承诺网页项目知识后台实时双向更新 |
| OpenAI dots | 用已授权的 GitHub 插件或连接电脑读取 | 遵循同一任务前后协议，在实际可写插件支持时提交 PR | dots 的独立笔记、ChatGPT memory 与本仓库是三个不同存储面；安装插件不自动建立监听任务 |
| Meta Muse / Muse Code | 有工具权限时读取公开 API；Muse Code 可通过其扩展机制接入 | 使用通用适配器或平台可用的 MCP / hooks | Muse 与 Muse Code 的能力不能混同；未在实际账号验证时不声称原生同步已接通 |
| DSH | 全局任务规则调用已安装的本机适配器，获取固定版本快照供会话读取 | 任务收尾规则调用适配器；只提交通过公开门禁的候选，详见 [DSH.md](DSH.md) | 任务规则不等于原生强制事件插件；适配器已实测，后续会话是否调用仍以工具记录、本机回执和 GitHub PR 为依据 |

## 本地通用命令

在仓库根目录使用 Python 3.10 或更高版本，不需要第三方 Python 包：

```sh
python scripts/archive.py read --output .local/profile-context.md
python scripts/archive.py record --input .local/event.json
python scripts/archive.py propose --input .local/event.json --publish
python scripts/archive.py validate
python scripts/archive.py restore --sha {{完整历史提交SHA}} --publish
```

`record` 仅生成本地文件；`propose --publish` 仅创建 PR。是否已经合并必须读取远端结果。`restore` 恢复五个档案目录，并保留当前脚本、安全配置和全部 Git 历史；无 `--publish` 时只预览。

认证优先使用已有 `GH_TOKEN` / `GITHUB_TOKEN` 环境变量，其次已登录的 GitHub CLI；没有这些时，可以在设备本地复用 Git Credential Manager 已保存的当前仓库所有者身份。适配器不导出、不保存、不展示凭据，也不自动发起登录。新设备首次写入仍需要该设备已有相应授权；公开读取可匿名进行。

## 任务结束事件

下面是协议示例，属于合成事件，不描述仓库所有者的私人经历：

```json
{
  "schema_version": 1,
  "event_id": "example-portable-markdown",
  "kind": "experience",
  "title": "Markdown 档案跨工具复用",
  "summary": "使用固定 Git 提交读取一组文档，可避免一次任务混入不同版本。",
  "source": "user-confirmed",
  "confirmed": true,
  "visibility": "public",
  "approved_for_public": true,
  "occurred_at": "2026-10-26T12:00:00+08:00"
}
```

`approved_for_public` 必须代表实际的公开授权，不能由程序为了通过校验而自动从 false 改为 true。密钥、手机号、身份证号、本机绝对路径等会被拒绝；模式扫描只能减少误发，不能证明所有内容都无隐私。身份信息默认保留模板，长期事实不得由推断填充。

## 版本保护与恢复

主分支要求 PR、通过 `archive-validation` 检查并满足当前基线；禁止强推与删除，规则同时约束管理员的日常写操作。低风险追加不额外要求人工审批，因此授权的任务结束更新可以自动完成。核心内容修改仍遵循用户明确授权和可审查 PR 的规则。

只读标签是文档协议，自动写入路径由脚本实际限制，GitHub 分支规则限制主分支写入。仓库管理员仍拥有配置治理规则的管理权；不能把任何单账号系统描述为绝对无法篡改。

任意完整历史 SHA 可以作为恢复目标，前提是它属于当前主分支历史且包含完整五目录。恢复通过新提交和 PR 执行；公开记录恢复后仍可能存在于历史与他人副本，恢复功能不是敏感数据撤回功能。

日常恢复可运行 `python scripts/dsh_adapter.py restore --sha {{完整历史提交SHA}} --publish`，一次调用创建恢复 PR、等待检查并请求合并。认证、检查或网络失败时会保留具体状态，不能声称已经恢复。

GitHub Actions 使用 `GITHUB_TOKEN` 创建的 PR 可能需要批准后才运行 PR 检查。本仓库的网页恢复演练实际遇到了该限制：所有者通过正常审批入口批准检查后，重跑原恢复作业成功。网页恢复入口虽会额外调度验证，但不能替代 GitHub 要求的原生 PR 检查审批。本机任务适配器使用已有用户认证从 Actions 外创建 PR，以便走正常检查链路；没有通过更改检查状态或关闭分支保护绕过审批。

## 官方资料

- [GitHub 分支保护](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Contents API 与版本 SHA](https://docs.github.com/en/rest/repos/contents)
- [GitHub Actions 触发行为](https://docs.github.com/actions/using-workflows/triggering-a-workflow)
- [ChatGPT GitHub 连接](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt)
- [Gemini GitHub 仓库导入](https://support.google.com/gemini/answer/16176929?hl=en)
- [Gemini API function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Claude GitHub 集成](https://support.claude.com/en/articles/10167454-use-the-github-integration)
- [dots 电脑和插件](https://learn.chatgpt.com/docs/dots/computers-and-apps)
- [dots 任务与记忆](https://learn.chatgpt.com/docs/dots/tasks-and-memory)
- [Meta Muse](https://ai.meta.com/muse/)
- [Muse Code 扩展](https://ai.developer.meta.com/docs/muse-code/extending)
