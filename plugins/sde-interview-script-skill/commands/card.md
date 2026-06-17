---
description: Turn pasted text into a diagram-first Excalidraw visual
argument-hint: [text]
---

Use the bundled `card` skill in this plugin to turn the following text into a diagram-first Excalidraw visual. Prefer decision trees, comparison maps, pipelines, architecture-style blocks, callouts, and small talk-track notes over long article-like script blocks.

Default to English unless the user explicitly requests Chinese or another language. If no text was provided in `$ARGUMENTS`, ask the user to paste the text. Return only the preview/link output that the skill produces.

Text:

$ARGUMENTS
