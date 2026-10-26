# AI-READONLY: DSH 接入与任务前后操作

本仓库提供 Python 标准库适配器 `scripts/dsh_adapter.py`。当前设备已安装指向此仓库的 DSH 全局任务规则和私有接入说明；DSH 读取该规则后，在任务开始和收尾时调用适配器。接入不修改 DSH 程序、不重启会话，也不新增常驻轮询服务。

这是一套由 DSH 任务规则驱动的工具流程。它不声称已经安装原生事件插件，也不保证在模型未执行规则、任务被中断或环境没有写入权限时仍能后台同步。每次成功都以适配器回执、GitHub PR 和合并提交为证据。其他设备需要自己的工具环境和写入授权。

## 开工：取得当前档案

在仓库根目录运行：

```sh
python scripts/dsh_adapter.py before-task
```

读取 JSON 返回的 `context_file`，将内容作为个人背景资料使用。返回值包含固定 Git 提交、文档数量和内容校验值；相同版本直接使用经过校验的缓存。远端不可用而缓存有效时返回 `offline-cache`，必须向使用者标明该版本不是实时刷新结果。

默认私有状态写入已被 Git 忽略的 `.local/dsh/`。当前设备使用仓库外的私有状态目录，并在 DSH 本地说明中给出具体路径；这些路径和缓存不会提交到 GitHub。`--state-dir` 是全局参数，必须写在子命令前。

## 收尾：自动提交合格事件

先按 [事件协议](ai-integration.md#任务结束事件) 生成事件 JSON。只有已确认、确有长期价值且明确允许公开的内容才能使用 `approved_for_public: true`。不应为了满足校验自动改写公开授权标志；不确定的内容保留在本机私有区。

```sh
python scripts/dsh_adapter.py after-task --input .local/event.json
```

一次调用依次完成：去重与公开内容检查、保存私有待处理候选、创建事件分支和 PR、等待必需检查、按准确的 PR head SHA 请求合并，以及合并后回读。只允许新增 `memory/entries/<event_id>.md`；不会自动改动身份、核心规则或已有记录。类型为 `skill`、`project` 的事件也先进入这个受限入口，整理至其他目录需另行授权。

| 返回状态 | 含义与下一步 |
| --- | --- |
| `merged` / `already-merged` / `already-present` | 远端已保存；报告 PR、提交及回读版本 |
| `pull-request` | 使用了 `--no-merge`，只创建 PR |
| `checks-pending` | 检查尚未完成；候选保留，用相同输入重试 |
| `checks-failed` / `merge-blocked` | 检查或保护阻止合并；修复具体原因，不关闭保护 |
| `error` | 输入、认证、冲突或网络等错误；不能宣称已经同步 |

同一事件并发调用会串行保护。同 ID、不同内容会拒绝；曾合并后又被历史恢复撤回的事件不会因重试而重新插入。失败候选保留供后续处理，无后台自动重试守护程序。

## 恢复历史：一条命令

将完整历史提交 SHA 交给 DSH，执行：

```sh
python scripts/dsh_adapter.py restore --sha {{完整历史提交SHA}} --publish
```

去掉 `--publish` 可先看预览。该命令创建恢复 PR、等待检查、请求合并并回读；恢复对象是五个档案目录，工具、安全配置及后续 Git 历史保留。目标必须是当前主分支的历史祖先且包含完整档案目录。检查、认证或网络失败会返回实际状态，不会绕过分支保护。

网页入口位于 [Restore archive content](https://github.com/lenwallem-bit/personal-ai-archive/actions/workflows/restore.yml)。该工作流用 GitHub Actions 身份创建 PR；GitHub 可能要求所有者先批准 PR 检查，再重跑恢复作业。本机适配器从 Actions 外使用当前设备已有授权创建 PR，适合作为日常恢复入口。

## 当前验收范围

已验证适配器在 DSH 工作区取得快照、生成真实记忆 PR、通过 GitHub 检查、合并和回读；历史恢复亦有远端成功记录，见 [交付报告](DELIVERY.md)。全局任务规则已安装并核对内容。

以上验证由搭建程序调用适配器完成，没有另外启动收费模型任务去冒充“DSH 模型亲自完成全流程”。后续 DSH 会话是否执行了任务规则，应查看它自己的工具调用及适配器回执。
