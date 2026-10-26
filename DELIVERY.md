# AI-READONLY: 个人 AI 档案搭建与验收报告

## 交付结果

公开仓库：[personal-ai-archive](https://github.com/lenwallem-bit/personal-ai-archive)。

仓库已建立统一的 Markdown 档案结构、跨 AI 读写约定、受限记录适配器、GitHub 检查及历史恢复流程。已通过真实记忆写回和真实历史恢复验证。初始文件保留清晰占位符，未根据其他聊天自动填充私人身份、职业或项目资料。

这次交付使支持联网或工具调用的 AI 能读取同一份档案，并使已授权的执行环境通过受检查的 PR 更新公开记忆。各平台账号的授权、原生记忆功能和自动触发能力仍需分别验证；仓库协议本身不会替所有平台完成账号连接。

## 目录与模板

五个核心目录各有一份使用说明和三份内容模板，共 **15 份内容模板**。另有自动事件目录说明及根目录接入、权限、沟通规则文件。

| 目录 | 用途 | 三份内容模板 |
| --- | --- | --- |
| `identity/` | 个人身份、职业、核心标签、人生目标和公开边界 | `profile.md`、`goals.md`、`boundaries.md` |
| `workflow/` | 工作习惯、常用工具、沟通方式、任务优先级与决策原则 | `preferences.md`、`tools.md`、`priorities.md` |
| `memory/` | 已确认偏好、重要决策和历史经验 | `preferences.md`、`decisions.md`、`lessons.md` |
| `skills/` | 已掌握技能、学习计划和待提升能力 | `competencies.md`、`learning-plan.md`、`growth.md` |
| `archive/` | 历史项目、旧文档索引和已完成任务摘要 | `projects.md`、`documents.md`、`completed-tasks.md` |

模板使用 `{{我的职业}}`、`{{常用沟通风格}}`、`{{核心决策原则}}` 等占位符，并明确 `template`、`unknown` 状态。所有 Markdown 首行使用 `AI-READONLY` 或 `AI-WRITABLE` 标签。AI 可直接读取 Markdown；未经确认的占位符不构成个人事实。

身份核心信息默认只读，需要用户明确授权具体变更。自动记录器只新增 `memory/entries/<event_id>.md`，不覆盖既有记忆、身份或治理配置。其他目录通过授权的 PR 更新。

## 快速使用

将以下文字作为新 AI 会话的背景指令：

```text
我的个人 AI 档案：
https://github.com/lenwallem-bit/personal-ai-archive

先读取 AGENTS.md、archive-manifest.json、identity/profile.md、workflow/preferences.md，
再按当前任务读取必要文件，并记录读取的提交 SHA。
占位符与 template/unknown 不是事实，当前明确指令优先。
任务完成后仅提炼适合公开且已确认的经验或偏好，按仓库规则去重、校验并通过 PR 写入。
没有写入工具或授权时返回候选内容，明确说明尚未保存。
```

完整操作见 [QUICKSTART.md](QUICKSTART.md)，平台能力和接入方式见 [ai-integration.md](ai-integration.md)，读写约束见 [AGENTS.md](AGENTS.md)。公开内容可通过 GitHub API 读取；适配器先固定提交 SHA，再读取该版本的文件，避免不同文件来自不同版本。

### 自动更新流程

完成任务后提炼候选，确认来源与公开范围，核对事件 ID 和已有记录，随后创建独立分支及 PR。检查通过后，已授权的完成器才尝试合并，并核对实际结果。遇到重复事件、内容冲突、检查失败或 GitHub 保护阻断时，保留明确状态，不覆盖主分支，也不宣称同步成功。

`approved_for_public` 等字段记录公开授权条件；它们不能替代用户的真实授权。模式扫描只能辅助发现敏感内容，不能保证识别所有私人信息。未明确适合公开的候选应保留在私有执行环境。

## 版本保护与恢复

`main` 已配置以下保护：

| 保护项 | 配置 |
| --- | --- |
| 合并入口 | 必须通过 PR |
| 必需检查 | `archive-validation` |
| 检查来源 | GitHub Actions，应用 ID `15368` |
| 分支最新状态要求 | `strict` 已启用 |
| 管理员 | 同样执行保护规则 |
| 强制推送与分支删除 | 禁止 |
| 提交历史 | 要求线性历史 |
| 必需人工审批数 | `0`，允许经检查的自动合并 |

文件标签是语义约定，实际自动写入范围由适配器限制；GitHub 保护负责 PR、检查和提交历史。该设计不宣称能阻止仓库所有者主动改变其管理设置。

历史恢复创建新的恢复分支、提交及 PR，将五个档案目录还原到指定历史快照，同时保留现有脚本、工作流和集成配置。恢复不会强制推送或抹除提交历史。

GitHub 网页入口是 [Restore archive snapshot](https://github.com/lenwallem-bit/personal-ai-archive/actions/workflows/restore.yml)。输入完整历史提交 SHA 后运行。**GitHub 可能出现 `action_required` 并要求仓库所有者批准运行；这种状态需要按平台要求批准，不能描述为无条件的一键完成。**

已配置的本地 DSH 执行环境也可使用以下命令，通过同样的 PR 与检查流程恢复：

```text
python scripts/dsh_adapter.py restore --sha <历史提交的完整40位SHA> --publish
```

不加 `--publish` 时只查看恢复预案。恢复会改变当前档案内容，应先确认目标版本；普通恢复也不会从已有 Git 历史和外部副本中擦除曾经公开的信息。

## 真实远端验证证据

| 验证项 | 实际结果 | 可核查证据 |
| --- | --- | --- |
| 仓库初始化 | 初始版本已提交 | [6796475f640624ab8752313220ec9366e1cf092d](https://github.com/lenwallem-bit/personal-ai-archive/commit/6796475f640624ab8752313220ec9366e1cf092d) |
| 公开记忆写回 | PR #1 已合并，完成真实写入链路验证 | [PR #1](https://github.com/lenwallem-bit/personal-ai-archive/pull/1)；[合并提交 819aa324a23057bcb5759cb35ac7e69916a0c1f7](https://github.com/lenwallem-bit/personal-ai-archive/commit/819aa324a23057bcb5759cb35ac7e69916a0c1f7) |
| 写回检查 | 真实 GitHub Actions 检查通过 | [运行 40321777266](https://github.com/lenwallem-bit/personal-ai-archive/actions/runs/40321777266) |
| 历史恢复 | PR #2 已合并，生成新的恢复提交 | [PR #2](https://github.com/lenwallem-bit/personal-ai-archive/pull/2)；[恢复提交 dd7f8bdbdb646d33ef15ea5ac612559cf5f4b0de](https://github.com/lenwallem-bit/personal-ai-archive/commit/dd7f8bdbdb646d33ef15ea5ac612559cf5f4b0de) |
| 恢复工作流 | 第 2 次尝试成功 | [运行 40321968966，attempt 2](https://github.com/lenwallem-bit/personal-ai-archive/actions/runs/40321968966/attempts/2) |
| 本机单命令恢复 | 适配器从 Actions 外创建 PR #3，检查通过后自动合并，无网页人工审批 | [PR #3](https://github.com/lenwallem-bit/personal-ai-archive/pull/3)；[提交 c6040d3a45117e7ec6b049bade4f0d48820967dd](https://github.com/lenwallem-bit/personal-ai-archive/commit/c6040d3a45117e7ec6b049bade4f0d48820967dd)；[检查 40323350738](https://github.com/lenwallem-bit/personal-ai-archive/actions/runs/40323350738) |

网页恢复先回到初始模板版本；本机恢复再回到 PR #1 的历史版本，保留一条公开的档案搭建决定作为示例。PR #3 合并后的文件树与指定历史版本完全相同，并保留两次恢复提交的历史。DSH 客户端回读该提交成功，快照包含 7 份入口及记忆文档。

这些证据分别证明初始版本、一次真实写回和两种入口的真实恢复。它们不等于所有 AI 平台都已经获得授权，也不表示未来每次更新都不会因网络、并发或平台审批而暂停。

## 跨平台接入状态

| 平台或执行环境 | 当前状态 | 完成边界 |
| --- | --- | --- |
| 当前 ChatGPT 会话的 GitHub 通道 | 已完成实际验证 | 已进行远端仓库操作和上述写回、检查、恢复验证 |
| DSH | 全局任务规则已安装，适配器实际读写已验证 | 任务前读取、任务后写回、恢复均有工具入口；规则驱动不等于原生强制后台同步，详见下节 |
| Gemini | 仓库协议与入口已提供 | 尚未在用户账号逐项授权及实测 |
| Claude | 仓库协议与入口已提供 | 尚未在用户账号逐项授权及实测 |
| Meta Muse | 通用档案协议可供适配 | 尚未确认用户环境的具体工具接口，未验证自动同步 |
| OpenAI Dots | 通用档案协议可供适配 | 尚未在用户账号验证具体同步接口与实际执行 |

`CLAUDE.md`、`GEMINI.md` 和统一 Markdown/API 协议提供可复用入口；平台能否直接读取、自动触发任务后写回或同步其内置记忆，取决于该平台当前实际工具和授权。无法联网的环境可以使用注明版本的 Markdown 快照。

## DSH 与最终验证补充

DSH 的全局 `AGENTS.md` 已追加独立接入管理块，原有内容逐字节保留并在设备私有区备份。本机接入说明指向实际客户端和仓库外状态目录。接入利用 DSH 已自动加载的任务规则：开工调用 `before-task` 并读取快照；收尾对合格候选调用 `after-task`。没有修改 DSH 程序、安装原生插件、启动新轮询服务或重启活跃会话。

客户端在该设备实际取得固定快照，并完成上表 PR #1 的提交、检查、合并和回读。公开事件只记录本仓库的通用设计决定，没有从其他聊天提取私人资料。此前已合并又被恢复撤回的事件，以相同事件 ID 重放时被实际拒绝，未重新写入远端。

这次测试由搭建程序调用 DSH 工作区内的适配器执行，没有额外启动模型任务去声称“DSH 模型已亲自完成全流程”。后续会话需遵循已安装规则，其实际执行以 DSH 工具调用和本机回执为准。完整操作与返回状态见 [DSH.md](DSH.md)。

| 最终代码验证 | 结果 |
| --- | --- |
| Linux 离线测试 | 28 项全部通过 |
| Windows 测试 | 27 项通过，1 项因系统创建符号链接需要权限而跳过；对应测试在 Linux 已通过 |
| Markdown 检查 | 首行标签、结构、大小及公开内容检查通过 |
| 独立代码复核 | 未发现必须阻止交付的 P0/P1 问题；并发事件锁、恢复 rename 范围检查和撤回事件防重放已补齐 |
| 中文工具回执 | 命令行统一使用 UTF-8 输出，适配 Windows 中文路径与 JSON 读取 |

维护修复、DSH 说明和本报告通过受保护的维护 PR 交付。当前文件的确切版本与合并记录可从 [提交历史](https://github.com/lenwallem-bit/personal-ai-archive/commits/main/DELIVERY.md) 核对，自动检查见 [Actions](https://github.com/lenwallem-bit/personal-ai-archive/actions)。
