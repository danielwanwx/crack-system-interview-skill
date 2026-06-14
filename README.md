# SDE Interview Script Skill

A Codex skill and plugin for turning technical interview excerpts into senior SDE speaking scripts and direct Excalidraw visual links.

Default output is intentionally short:

- one-sentence summary in Chinese and English
- a Chinese 90-120 second interview answer
- a short English version
- an Excalidraw-default-style script card with blue decision-flow boxes when MCP export is available
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

The default board is a hybrid script card, not a colorful flowchart. It should include the actual Chinese speaking script, a blue decision flow, and the 30-second version inside the drawing. It should keep Excalidraw's default-feeling font and sketch style, with generous padding and comfortable line spacing.

When exporting to excalidraw.com, text must be real Excalidraw `text` elements. Do not rely on MCP-only `label` shorthand in shapes, because it can export as blank boxes.

When Excalidraw MCP tools are unavailable, it should create a `.excalidraw` file and return the file path. It should output an Excalidraw Board Brief only if neither direct export nor file creation is available.

Example GraphQL test link:

https://excalidraw.com/#json=Qw-QKCMgvVK7VfDktC4N6,fvQ9vSqSgnMuvK4Y-O1vkQ

## 中文说明

这个 Codex skill/plugin 会把技术面试材料转换成 senior SDE candidate 可以直接讲的短答案，并优先生成可以直接打开的 Excalidraw 链接。

默认输出包括：

- 中文和英文一句话总结
- 中文 90-120 秒面试版
- 英文短版
- Excalidraw 默认风格讲稿区 + 蓝色判断流程链接，或 `.excalidraw` 文件路径
- 中文 30 秒短版
- 必要时只补一个高概率追问点
