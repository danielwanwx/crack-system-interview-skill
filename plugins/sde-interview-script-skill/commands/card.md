---
description: Digest hard text into an interview whiteboard and talk track
argument-hint: [text]
---

Use the bundled `card` skill in this plugin to help the user digest the following material. Produce a coherent Excalidraw whiteboard sample, editable link or path, and concise talk track. Prefer decision trees, comparison maps, pipelines, architecture-style blocks, callouts, and small talk-track notes over long article-like script blocks.

Default to English unless the user explicitly requests Chinese or another language. If no text was provided in `$ARGUMENTS`, ask the user to paste the text. Return the preview/link output plus the copyable talk track when the source is interview prep, system design, API design, or technical study material.

Text:

$ARGUMENTS
