# SDE Interview Script Skill

A cross-agent plugin/skill package for turning pasted text into Excalidraw-style whiteboard visuals. It uses native Excalidraw blocks: dashed task/constraints frames, light-blue component blocks, black arrows, circles/squares/rectangles, and sticky notes for gotchas. It avoids decorative component icons by default so layout stays clean and predictable. It includes a short `$card` entrypoint for general text and a backward-compatible `$senior-sde-interview-script` entrypoint for SDE interview prep. Output language defaults to English, and users can request Chinese or another language in the prompt.

## Simplest Usage

Codex or Cursor:

```text
Use $card: <paste text here>
```

Chinese:

```text
Use $card in Chinese: <paste text here>
```

Claude Code:

```text
/card <paste text here>
```

Natural language also works after installation:

```text
Turn this into an Excalidraw card: <paste text here>
```

Default output is intentionally minimal:

- a direct preview image when the host can display local images
- an editable Excalidraw link when upload succeeds
- a local `.excalidraw` path as fallback

The generated board explains the material through native blocks, arrows, comparisons, system-design component diagrams, and sticky-note callouts. It should look like a clean interview whiteboard, not a long essay pasted into a box. Text should prefer one sentence per line when it fits, with left-aligned block content and rows that use the available width. The chat reply should not repeat the visual text unless the user explicitly asks for copyable text.

The content step is intentionally LLM-heavy: the agent should first infer what a strong candidate would understand, then split output into two layers. The board contains professional whiteboard content: design choices, mechanisms, constraints, data flows, and tradeoffs. The `talk_track` contains the candidate-ready wording. Blocks should not be keyword flashcards, but they also should not sound like coaching notes.

The agent should also do an automatic source-sufficiency check. If the pasted text is already complete, it should only condense and structure it. If the text is partial or thin, it should fill the missing stable background needed for a useful board and talk track, such as mechanisms, tradeoffs, examples, caveats, or production implications. Browsing is reserved for current, version-specific, product-specific, niche, or high-stakes facts; when browsing is used, prefer primary or authoritative sources. The JSON can include `source_notes` with `completeness`, `completion_mode`, `added_points`, and `uncertain_points`, but those notes are not rendered by default.

Before drawing, the agent should do a compact pre-drawing plan. For short material, a single comparison, pipeline, concept map, or architecture board is usually enough. For larger system-design material, use `layout: "modular-composite"` and split the board into modules. Good signals for modular mode include: more than five meaningful entities, more than two flows, multiple technical types (API, storage, cache, queue, consistency, failure recovery), or a source paragraph that mixes requirements, architecture, tradeoffs, and failure modes.

The planning shape can be embedded in the JSON so another host can understand the intent:

```json
{
  "planning": {
    "complexity": "high",
    "diagram_strategy": "modular-composite",
    "reason": "The source mixes read path, booking path, inventory consistency, payment failure handling, and operational tradeoffs.",
    "signals": {
      "entities": 9,
      "flows": 4,
      "technical_types": ["API", "cache", "queue", "database", "consistency", "payment"]
    },
    "modules": [
      {"id": "overview", "title": "System overview", "layout": "overview", "full_width": true},
      {"id": "browse", "title": "Browse/read path", "layout": "pipeline"},
      {"id": "booking", "title": "Booking/write path", "layout": "pipeline"},
      {"id": "inventory", "title": "Consistency boundary", "layout": "concept"},
      {"id": "payment", "title": "Payment recovery", "layout": "pipeline"}
    ]
  }
}
```

Blocks can then set `"module": "booking"` or any matching module id. The renderer draws dashed module frames and keeps arrows routed around unrelated blocks.

The renderer follows the Excalidraw+ docs model as closely as possible while staying offline-compatible: scenes are built from native Excalidraw blocks and connector elements, with semantic metadata for blocks, labels, and arrows. The local renderer does not require the Excalidraw+ MCP, but the same JSON structure can be adapted to MCP `edit_scene_content` flows when a host exposes that tool.

## Recommended Architecture

The best compatibility model is:

1. **Plugin manifests per host**: Codex, Cursor, and Claude Code each get their own marketplace/plugin manifest.
2. **Short primary skill**: all hosts load `skills/card/SKILL.md` as the easiest diagram-first entrypoint.
3. **SDE preset skill**: `skills/senior-sde-interview-script/SKILL.md` remains available for users who want the explicit SDE interview workflow.
4. **Bundled renderer scripts**: the agent writes a small content JSON, then runs `scripts/render_interview_card.py` to generate the preview SVG, `.excalidraw` file, and optional Excalidraw share link.
5. **Optional MCP**: Excalidraw MCP is declared for hosts that support it, but it is not required for the main flow.

Renderer invariants:

- Text must fit inside its parent block; blocks grow vertically when needed.
- Connectors leave from block edges and route around unrelated blocks.
- Connectors should leave and enter block edges perpendicularly using short port stubs; avoid long segments that run parallel against a block border.
- Connector labels should read as line annotations: keep them close to the line, slightly offset from the stroke, and only move them farther when needed to avoid blocks.
- Whiteboard previews keep bottom padding beyond the lowest block so screenshots and SVG previews do not crop the final row.
- Decorative icons are opt-in, because they reduce text width and increase overlap risk.

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
  commands/card.md                                   # Claude Code short command: /card
  skills/card/
    SKILL.md
    scripts/render_interview_card.py
    scripts/share_excalidraw.mjs
  skills/senior-sde-interview-script/
    SKILL.md
    scripts/render_interview_card.py
    scripts/share_excalidraw.mjs
card/                                                # standalone short skill copy
senior-sde-interview-script/                         # standalone skill copy
scripts/                                             # repo-level renderer test copy
```

## End-To-End Flow

After the plugin or skill is installed in a host:

1. User pastes a Hello Interview/API/system-design paragraph.
2. User optionally specifies language, for example `in Chinese`, `用中文`, `in Spanish`, or `bilingual English and Chinese`. If no language is specified, the skill uses English.
3. The agent invokes `card` by default, or `senior-sde-interview-script` for the explicit SDE preset.
4. The skill tells the agent to create a diagram JSON object:

```json
{
  "title": "CAP in Interviews",
  "language": "English",
  "style": "excalidraw-plus",
  "layout": "comparison",
  "planning": {
    "complexity": "medium",
    "diagram_strategy": "comparison",
    "reason": "The source is a CP versus AP tradeoff."
  },
  "summary": "CAP is a partition-time product decision.",
  "task": "Ask which failure hurts more during a partition: stale data or failed requests.",
  "constraints": [
    "Partition tolerance is mandatory",
    "The choice affects storage, cache, replication, and fallback strategy"
  ],
  "blocks": [
    {
      "id": "cp",
      "lane": "left",
      "kind": "component",
      "title": "CP for expensive wrong state",
      "body": "Inventory, payment, and seat holds cannot confirm stale state. Use conditional writes, transactions, or strong reads; degrade instead of accepting double booking."
    },
    {
      "id": "ap",
      "lane": "right",
      "kind": "component",
      "title": "AP for freshness-as-UX",
      "body": "Browsing, feeds, and recommendations can tolerate short-lived stale data. Serve from replicas or cache, then converge asynchronously."
    }
  ],
  "connectors": [
    {"from": "cp", "to": "ap", "label": "same partition, different product priority"}
  ],
  "callouts": [
    {"title": "Partition-time choice", "body": "Once a network partition exists, the practical tradeoff is stale reads versus failed requests."}
  ],
  "talk_track": "I would first ask which failure mode the product can tolerate: stale data or temporary unavailability."
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
Use $card: <paste text here>
```

Chinese output:

```text
Use $card in Chinese: <paste text here>
```

Other languages:

```text
Use $card in Spanish: <paste text here>
```

Bilingual:

```text
Use $card bilingual English and Chinese: <paste text here>
```

## Release QA

Before cutting a release, run the full offline gate:

```bash
python3 scripts/run_release_qa.py --out /tmp/hello-interview-release-qa
```

The gate renders the curated Hello Interview smoke set plus release-specific
fixtures, then validates:

- all six layouts: `architecture`, `comparison`, `concept-map`, `decision`, `modular-composite`, `pipeline`
- Hello Interview chapter styles: In a Hurry framework chapters, API design, core concepts, key technologies, patterns, advanced topics, and problem breakdowns
- short, medium, and long content
- Chinese and English output
- native Excalidraw blocks, handwritten text images, connector routing, connector-label proximity, and bottom canvas padding
- Codex, Cursor, and Claude plugin manifests plus synchronized renderer copies
- auto-completion coverage for thin or partial sources via `source_notes`

Network share links are intentionally outside the offline gate. To smoke-test
link generation for one rendered board:

```bash
node scripts/share_excalidraw.mjs --input /tmp/hello-interview-release-qa/<case>/<case>.excalidraw
```

## Install In Codex

Add this repository as a Codex plugin marketplace:

```bash
codex plugin marketplace add danielwanwx/sde-interview-script-skill
```

Then install `Script Card` from the `Script Card Skills` marketplace.

Prompt:

```text
Use $card: <paste text here>
```

## Install In Cursor

This repo includes Cursor marketplace and plugin manifests:

- `.cursor-plugin/marketplace.json`
- `plugins/sde-interview-script-skill/.cursor-plugin/plugin.json`

Import the repository as a Cursor plugin marketplace or team plugin source. The plugin loads:

- `skills/`
- optional `mcp.json`
- bundled renderer scripts under the skill

After installation, paste the excerpt and ask Cursor to use `$card`. Cursor-capable chats should display the local preview image plus the Excalidraw link/path.

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

Use the short slash command:

```text
/card <paste text here>
```

Claude Code terminal usually cannot inline local images, so the skill defaults to returning the Excalidraw link. If upload is unavailable, it returns the local preview SVG and `.excalidraw` paths.

## Standalone Skill

If you only want the skill folder:

```text
Use $skill-installer to install https://github.com/danielwanwx/sde-interview-script-skill/tree/main/card
```

Or copy `card/` manually into the host's skill directory. The longer `senior-sde-interview-script/` standalone skill remains available for explicit SDE interview prep.

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

安装后，最简单的调用就是 `Use $card: <粘贴文本>`。如果在 Claude Code 里，用 `/card <粘贴文本>`。默认输出英文；如果 prompt 里写 `用中文`、`Chinese`、`Spanish` 或其他语言，就按指定语言输出。聊天回复默认只给图片和链接。
