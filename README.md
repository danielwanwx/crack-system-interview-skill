# SDE Interview Script Skill

A cross-agent plugin/skill package for turning technical interview excerpts into senior SDE speaking scripts embedded in Excalidraw-style visuals. Output language defaults to English, and users can request Chinese or another language in the prompt.

Default output is intentionally minimal:

- a direct preview image when the host can display local images
- an editable Excalidraw link when upload succeeds
- a local `.excalidraw` path as fallback

The generated board contains the one-sentence summary, interview answer, compact decision flow, and 30-second version in the target language. The chat reply should not repeat that text unless the user explicitly asks for copyable text.

## Recommended Architecture

The best compatibility model is:

1. **Plugin manifests per host**: Codex, Cursor, and Claude Code each get their own marketplace/plugin manifest.
2. **One shared Agent Skill**: all hosts load the same `skills/senior-sde-interview-script/SKILL.md` workflow.
3. **Bundled renderer scripts**: the agent writes a small content JSON, then runs `scripts/render_interview_card.py` to generate the preview SVG, `.excalidraw` file, and optional Excalidraw share link.
4. **Optional MCP**: Excalidraw MCP is declared for hosts that support it, but it is not required for the main flow.

This is deliberately not a `rules` or `CLAUDE.md` package. Rules are too host-specific and passive; plugin + skill packaging gives installable discovery, namespaced invocation, bundled scripts, and optional MCP wiring.

## Repository Layout

```text
.agents/plugins/marketplace.json                     # Codex marketplace
.cursor-plugin/marketplace.json                      # Cursor marketplace
.claude-plugin/marketplace.json                      # Claude Code marketplace
plugins/sde-interview-script-skill/
  .codex-plugin/plugin.json
  .cursor-plugin/plugin.json
  .claude-plugin/plugin.json
  .mcp.json                                          # Claude/Codex MCP config
  mcp.json                                           # Cursor MCP config
  skills/senior-sde-interview-script/
    SKILL.md
    scripts/render_interview_card.py
    scripts/share_excalidraw.mjs
senior-sde-interview-script/                         # standalone skill copy
scripts/                                             # repo-level renderer test copy
```

## End-To-End Flow

After the plugin or skill is installed in a host:

1. User pastes a Hello Interview/API/system-design paragraph.
2. User optionally specifies language, for example `in Chinese`, `用中文`, `in Spanish`, or `bilingual English and Chinese`. If no language is specified, the skill uses English.
3. The agent invokes `senior-sde-interview-script`.
4. The skill tells the agent to create a compact JSON object:

```json
{
  "title": "GraphQL",
  "language": "English",
  "summary": "One short sentence explaining the core interview idea.",
  "script": "A 90-120 second senior SDE interview answer in the target language.",
  "short": "A 30-second version in the target language.",
  "flows": ["Signal / pain", "When it fits", "Tradeoff", "Decision"]
}
```

5. The agent runs the bundled renderer:

```bash
python3 scripts/render_interview_card.py \
  --content /tmp/interview-card.json \
  --out /tmp/interview-card \
  --slug interview-card
```

6. The renderer writes:

```json
{
  "preview": "/tmp/interview-card/interview-card-preview.svg",
  "excalidraw": "/tmp/interview-card/interview-card.excalidraw",
  "link": "https://excalidraw.com/#json=..."
}
```

7. Codex/Cursor reply with only the preview image and link/path. Claude Code terminal replies with the link first, then local paths if needed.

## Language Selection

Default output language is English:

```text
Use $senior-sde-interview-script to turn this excerpt into a senior SDE Excalidraw-style preview image and link only.
```

Chinese output:

```text
Use $senior-sde-interview-script to turn this excerpt into a senior SDE interview script and Excalidraw card. Use Chinese. Only output the image and link.
```

Other languages:

```text
Use $senior-sde-interview-script to turn this excerpt into a senior SDE interview script and Excalidraw card. Output in Spanish. Only output the image and link.
```

Bilingual:

```text
Use $senior-sde-interview-script to turn this excerpt into a senior SDE interview script and Excalidraw card. Use bilingual English and Chinese. Only output the image and link.
```

## Install In Codex

Add this repository as a Codex plugin marketplace:

```bash
codex plugin marketplace add danielwanwx/sde-interview-script-skill
```

Then install `SDE Interview Script` from the `SDE Interview Script Skills` marketplace.

Prompt:

```text
Use $senior-sde-interview-script to turn this excerpt into a senior SDE Excalidraw-style preview image and link only. Default to English unless I specify another language.
```

## Install In Cursor

This repo includes Cursor marketplace and plugin manifests:

- `.cursor-plugin/marketplace.json`
- `plugins/sde-interview-script-skill/.cursor-plugin/plugin.json`

Import the repository as a Cursor plugin marketplace or team plugin source. The plugin loads:

- `skills/`
- optional `mcp.json`
- bundled renderer scripts under the skill

After installation, paste the excerpt and ask Cursor to use the `senior-sde-interview-script` skill. Cursor-capable chats should display the local preview image plus the Excalidraw link/path.

## Install In Claude Code

This repo includes Claude Code marketplace and plugin manifests:

- `.claude-plugin/marketplace.json`
- `plugins/sde-interview-script-skill/.claude-plugin/plugin.json`

For local testing:

```bash
claude --plugin-dir ./plugins/sde-interview-script-skill
```

Marketplace install flow:

```text
/plugin marketplace add danielwanwx/sde-interview-script-skill
/plugin install sde-interview-script-skill@sde-interview-script-skill
```

Claude Code plugin skills are namespaced, so invoke:

```text
/sde-interview-script-skill:senior-sde-interview-script <paste excerpt here>
```

Claude Code terminal usually cannot inline local images, so the skill defaults to returning the Excalidraw link. If upload is unavailable, it returns the local preview SVG and `.excalidraw` paths.

## Standalone Skill

If you only want the skill folder:

```text
Use $skill-installer to install https://github.com/danielwanwx/sde-interview-script-skill/tree/main/senior-sde-interview-script
```

Or copy it manually into the host's skill directory.

## Local Renderer Test

Create a content JSON and run:

```bash
python3 scripts/render_interview_card.py \
  --content /tmp/interview-card.json \
  --out /tmp/interview-card \
  --slug interview-card
```

The script uses only Python standard library. If Node.js and network access are available, it also uploads the `.excalidraw` scene to Excalidraw's share endpoint. Without Node.js or network access, the local preview SVG and `.excalidraw` file still work.

## Practical Limit

No agent host should auto-enable arbitrary cloned plugins without user trust. So a literal zero-click install after `git clone` is not realistic across Codex, Cursor, and Claude Code. The closest safe, portable target is what this repo implements: once the host imports or installs the plugin, the actual user workflow is copy paragraph in, get preview image plus link out.

## 中文说明

这个 repo 不是单纯的 prompt 或规则文件，而是跨宿主的 plugin + skill 包：

- Codex 用 `.agents` / `.codex-plugin`
- Cursor 用 `.cursor-plugin`
- Claude Code 用 `.claude-plugin`
- 三者共享同一个 `SKILL.md` 和渲染脚本

安装后，用户只需要粘贴原文段落，agent 会自动生成简短但有 senior 深度的面试讲稿，并把讲稿、判断流程和 30 秒短版放进 Excalidraw 风格图片里。默认输出英文；如果 prompt 里写 `用中文`、`Chinese`、`Spanish` 或其他语言，就按指定语言输出。聊天回复默认只给图片和链接。
