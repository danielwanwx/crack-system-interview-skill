# SDE Interview Script Skill

A Codex skill and plugin for turning technical interview excerpts into concise senior SDE speaking scripts and direct Excalidraw visual links.

Default output is intentionally short:

- one-sentence summary in Chinese and English
- a Chinese 60-90 second interview answer
- a short English version
- a direct Excalidraw link when MCP export is available
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
Use $senior-sde-interview-script to turn this excerpt into a concise SDE answer and Excalidraw link.
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
Use $senior-sde-interview-script to turn this technical excerpt into a concise senior SDE interview answer and Excalidraw visual.
```

## Excalidraw behavior

When Excalidraw MCP tools are available, the skill should call `create_view`, export with `export_to_excalidraw`, and return the Excalidraw URL directly.

When Excalidraw MCP tools are unavailable, it should create a `.excalidraw` file and return the file path. It should output an Excalidraw Board Brief only if neither direct export nor file creation is available.

Example GraphQL test link:

https://excalidraw.com/#json=46_L3r6YqyjSZPJSe9ple,cIKH4F0haZ4Pw8Vewr3UrQ

## 中文说明

这个 Codex skill/plugin 会把技术面试材料转换成 senior SDE candidate 可以直接讲的短答案，并优先生成可以直接打开的 Excalidraw 链接。

默认输出包括：

- 中文和英文一句话总结
- 中文 60-90 秒面试版
- 英文短版
- Excalidraw 直达链接，或 `.excalidraw` 文件路径
- 中文 30 秒短版
- 必要时只补一个高概率追问点
