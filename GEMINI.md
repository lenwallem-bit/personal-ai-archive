# AI-READONLY: Gemini 档案读取入口

请先读取 [AGENTS.md](AGENTS.md) 和 [archive-manifest.json](archive-manifest.json)，再读取 `identity/profile.md`、`workflow/preferences.md` 及当前任务必要的文件。

该文件提供统一入口，不会自行启用 GitHub 连接或后台同步。只有当前环境支持的工具才能请求 GitHub API；链接或仓库文件本身不会赋予 API 权限。不要把模板占位符当成已确认事实。

完成任务后按 `AGENTS.md` 提炼可公开的候选记忆。自动记录器仅追加 `memory/entries/<event_id>.md`，通过检查和 PR 留下版本记录。身份核心信息不得未经用户明确授权改动。

若当前环境没有写入能力，返回候选记录和目标路径，明确说明尚未写入。
