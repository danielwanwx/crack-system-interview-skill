# SDE Interview Script Skill

A Codex skill and plugin for turning technical interview excerpts into senior SDE speaking scripts embedded in Excalidraw visuals, with screenshot-and-link-only chat replies by default.

Default chat output is intentionally minimal:

- a direct in-chat preview image of the handwritten Excalidraw script card
- an editable Excalidraw link, or a `.excalidraw` file path as backup

The generated board itself contains the one-sentence summary, Chinese interview answer, compact decision flow, and 30-second version. The chat reply should not repeat that text unless the user explicitly asks for copyable text.

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

When Excalidraw MCP tools are available, the skill should call `create_view`, export with `export_to_excalidraw`, show a rendered preview image directly in chat, and return the Excalidraw URL as an editable backup. By default, the final response should only contain the screenshot and link/path.

The default board is a hybrid script card, not a colorful flowchart. It should include the actual Chinese speaking script, a blue decision flow, and the 30-second version inside the drawing. All cards, boxes, and frames should have transparent backgrounds with hand-drawn strokes only. Use black or dark gray strokes for script cards, and blue strokes/text/arrows for decision-flow boxes. Do not use blue or gray fills.

It should use Excalidraw's hand-drawn font style (`fontFamily: 1`) for editable text, plus rendered Chinese handwriting images when CJK glyphs would otherwise fall back to a plain font.

For Chinese handwriting, the skill prefers HanziPen-style rendering and embeds transparent PNG/SVG blocks in the Excalidraw file. This makes Chinese look handwritten too, with the tradeoff that those Chinese blocks are not directly editable as Excalidraw text.

When exporting to excalidraw.com, editable text must be real Excalidraw `text` elements. Do not rely on MCP-only `label` shorthand in shapes, because it can export as blank boxes. If Chinese handwriting is embedded as image blocks, the share-link export must also include/upload the related `files` data, otherwise the opened link can show blank image placeholders.

When Excalidraw MCP tools are unavailable, it should create a `.excalidraw` file and return the file path. It should output an Excalidraw Board Brief only if neither direct export nor file creation is available.

Example GraphQL test link:

https://excalidraw.com/#json=8gKTecAEUwJp5d7gU9Cuw,AqB6Qd5bVIOuuzx9786Rdw

## 中文说明

这个 Codex skill/plugin 会把技术面试材料转换成 senior SDE candidate 可以直接讲的短答案，并优先生成可以直接打开的 Excalidraw 链接。

默认输出包括：

- 直接显示在 chat 里的中文手写 Excalidraw 截图
- Excalidraw 链接或 `.excalidraw` 文件路径作为备份

讲稿正文、30 秒短版、判断流程都放在图里；除非明确要求可复制文本，回复里不重复展开。
