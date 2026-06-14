# SDE Interview Script Skill

A Codex skill and plugin for turning technical interview excerpts into speakable senior SDE interview answers and Excalidraw visual boards.

The workflow produces bilingual Chinese and English output by default:

- one-sentence summaries in Chinese and English
- a Chinese speakable interview answer
- an English speakable interview answer
- an Excalidraw-first visual explanation
- 30-second versions in both languages
- optional bilingual follow-up prep for senior-level tradeoffs and edge cases

## Install as a plugin

The plugin includes the skill plus an Excalidraw MCP server declaration.

Add this repo as a Codex plugin marketplace:

```bash
codex plugin marketplace add danielwanwx/sde-interview-script-skill
```

Then open the plugin directory in Codex, choose the `SDE Interview Script Skills` marketplace, and install `SDE Interview Script`.

After installing, ask:

```text
Use $senior-sde-interview-script to turn this excerpt into bilingual SDE scripts and an Excalidraw board.
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
Use $senior-sde-interview-script to turn this technical excerpt into bilingual senior SDE interview scripts and an Excalidraw visual.
```

## Excalidraw behavior

When Excalidraw MCP tools are available, the skill should draw the board directly in Excalidraw.

When Excalidraw MCP tools are unavailable, it outputs an Excalidraw Board Brief with exact boxes, arrows, labels, layout, and color grouping so the board can be recreated in Excalidraw.

## 中文说明

这个 Codex skill/plugin 会把技术面试材料转换成 senior SDE candidate 可以直接讲的中英文面试底稿，并同步生成 Excalidraw 风格的可视化讲解图。

默认输出包括：

- 中文和英文一句话总结
- 中文可直接讲版本
- 英文可直接讲版本
- Excalidraw 可视化讲解图或 Excalidraw Board Brief
- 中英文 30 秒短版
- 必要时补充中英文追问准备
