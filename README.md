# SDE Interview Script Skill

A Codex skill and plugin for turning technical interview excerpts into senior SDE speaking scripts and direct Excalidraw visual links.

Default output is intentionally short:

- one-sentence summary in Chinese and English
- a Chinese 90-120 second interview answer
- a short English version
- a handwritten Chinese/English Excalidraw script card with blue decision-flow boxes when MCP export is available
- a compact 30-second Chinese version
- only one follow-up gotcha when it is clearly useful

## Install as a plugin

The plugin includes the skill plus an Excalidraw MCP server declaration.

Add this repo as a Codex plugin marketplace:

```bash
codex plugin marketplace add danielwanwx/sde-interview-script-skill
```

Then open the plugin directory in Codex, choose the `SDE Interview Script Skills` marketplace, and install `SDE Interview Script`.

After installing, ask:

```text
Use $senior-sde-interview-script to turn this excerpt into a senior SDE answer and Excalidraw card.
```

## Install as a skill only

If you only want the prompt workflow without plugin packaging, install the skill directly:

```text
Use $skill-installer to install https://github.com/danielwanwx/sde-interview-script-skill/tree/main/senior-sde-interview-script
```

Or copy the skill folder manually:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/danielwanwx/sde-interview-script-skill.git /tmp/sde-interview-script-skill
cp -R /tmp/sde-interview-script-skill/senior-sde-interview-script ~/.codex/skills/
```

Then start a new Codex session and invoke:

```text
Use $senior-sde-interview-script to turn this technical excerpt into a senior SDE interview answer and Excalidraw visual.
```

## Excalidraw behavior

When Excalidraw MCP tools are available, the skill should call `create_view`, export with `export_to_excalidraw`, and return the Excalidraw URL directly.

The default board is a hybrid script card, not a colorful flowchart. It should include the actual Chinese speaking script, a blue decision flow, and the 30-second version inside the drawing. It should use Excalidraw's hand-drawn font style (`fontFamily: 1`) for editable text, plus rendered Chinese handwriting images when CJK glyphs would otherwise fall back to a plain font.

For Chinese handwriting, the skill prefers HanziPen-style rendering and embeds transparent PNG/SVG blocks in the Excalidraw file. This makes Chinese look handwritten too, with the tradeoff that those Chinese blocks are not directly editable as Excalidraw text.

When exporting to excalidraw.com, editable text must be real Excalidraw `text` elements. Do not rely on MCP-only `label` shorthand in shapes, because it can export as blank boxes. If Chinese handwriting is embedded as image blocks, the share-link export must also include/upload the related `files` data, otherwise the opened link can show blank image placeholders.

When Excalidraw MCP tools are unavailable, it should create a `.excalidraw` file and return the file path. It should output an Excalidraw Board Brief only if neither direct export nor file creation is available.

Example GraphQL test link:

https://excalidraw.com/#json=8gKTecAEUwJp5d7gU9Cuw,AqB6Qd5bVIOuuzx9786Rdw

## 中文说明

这个 Codex skill/plugin 会把技术面试材料转换成 senior SDE candidate 可以直接讲的短答案，并优先生成可以直接打开的 Excalidraw 链接。

默认输出包括：

- 中文和英文一句话总结
- 中文 90-120 秒面试版
- 英文短版
- 中文也手写的 Excalidraw 讲稿区 + 蓝色判断流程链接，或 `.excalidraw` 文件路径
- 中文 30 秒短版
- 必要时只补一个高概率追问点
