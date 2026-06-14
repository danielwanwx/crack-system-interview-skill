---
name: senior-sde-interview-script
description: "Convert Hello Interview excerpts, system design notes, API design notes, or other technical interview material into senior SDE interview speaking scripts embedded in Excalidraw visuals, with screenshot-and-link-only chat replies by default. Use when the user provides source paragraphs and asks for a concise but solid speakable interview answer, memorization-friendly draft, bilingual Chinese/English version, 30-second version, Excalidraw diagram, or asks to preserve this response pattern. Also use when the user wants answers to sound senior, practical, opinionated, and interview-ready without becoming textbook-like, overly long, or overly autobiographical."
---

# Senior SDE Interview Script

## Overview

Turn technical source material into a short answer a senior SDE candidate can actually say in an interview, then map the same content into an Excalidraw visual. Preserve the source's intent, but do not try to cover every pasted detail. Pick the points an interviewer is likely testing.

## Core Output

Unless the user asks for a different structure, generate the following content for the Excalidraw board:

- **一句话总结 / One-Sentence Summary**: one short Chinese sentence and one short English sentence explaining what the paragraph is about.
- **中文面试版**: 2 short Chinese paragraphs, suitable for a 90-120 second spoken answer.
- **English Short Version**: one short English paragraph with the same judgment and examples, not a literal translation.
- **Excalidraw Visual**: show a rendered preview image directly in chat whenever possible, and include a direct Excalidraw share link as the editable backup. The board must include the speakable script text, not just empty concept boxes. Chinese text should look handwritten too, not only English. If MCP export is not available, create a `.excalidraw` file and return the path. Use a Board Brief only as the last fallback.
- **30 秒短版**: one compact Chinese answer, at most two sentences.
- **追问准备 / Follow-Up Prep**: omit by default. Add only one short gotcha when it is highly likely to be asked or the user requests it.

Default chat reply must contain only the rendered preview image and the Excalidraw link or `.excalidraw` path. Do not repeat the summary, Chinese answer, English version, 30-second version, or follow-up text outside the image unless the user explicitly asks for copyable text.

## Workflow

1. Infer the likely interview question behind the excerpt.
2. Start with one concise Chinese summary sentence and one concise English summary sentence.
3. Extract only 4-5 interview-useful points:
   - the decision rule
   - when to use it
   - one realistic example
   - one senior caveat or tradeoff
   - one production implication when it changes the decision
4. Reframe the material as a senior candidate evaluating a real design situation.
5. Add practical depth only when it changes the decision: retries, caching, authorization, consistency, client contracts, observability, or operational cost.
6. Create the Excalidraw visual as a hybrid script card with a blue decision flow and prefer a direct share link.
7. End with a crisp principle the candidate can remember.

## Length Budget

- Chinese live answer: 90-120 seconds, usually 2 short paragraphs.
- English answer: max 1 short paragraph.
- 30-second version: max 2 Chinese sentences.
- Follow-up prep: omit unless asked, or include exactly one obvious gotcha.
- Do not enumerate every detail from the excerpt. Show judgment, not coverage.

## Voice And Stance

Produce Chinese first by default. Include English unless the user asks for Chinese only.

Use a candidate-owned point of view without sounding like a diary. Good phrases:

- "这个问题我会先看..."
- "我的判断标准是..."
- "我会倾向于..."
- "在实际设计里，我会关注..."
- "这里关键不是...而是..."

Avoid repeating "我在项目中..." or "当我遇到..." in every paragraph. The answer should sound like a senior candidate standing in front of the problem, making a clear judgment, and explaining why.

## Senior-Level Signal

Make the answer feel senior by including the practical reason behind the rule, not just the definition. Prefer one concrete API, data, or distributed-systems example, plus one boundary condition such as when not to use the pattern, what breaks at scale, how retries/caching/auth affect the design, or what the client contract implies.

Keep the language plain. Avoid buzzword stacks and concept dumps.

## Excalidraw Visual Workflow

Prefer Excalidraw over Mermaid or generic diagrams. Do not use Mermaid unless the user explicitly asks for Mermaid.

Default to a clean hybrid board:

- white background
- black or dark gray strokes
- transparent backgrounds for all cards, boxes, and frames (`backgroundColor: transparent`)
- black or dark gray strokes for script, summary, and 30-second cards
- blue strokes, text, and arrows only for the decision-flow boxes (`#2563eb`); do not use blue fills
- no rainbow palettes, decorative colors, or five-color flowcharts
- Excalidraw handwritten typography and sketch style: set editable text `fontFamily` to `1` for Excalidraw's hand-drawn/Virgil-style font, use rough hand-drawn shapes, and avoid polished slide-deck typography

The diagram should be a **script card plus decision flow**, not a sparse flowchart. It must stand on its own when opened:

- title + one-sentence summary
- large Chinese interview script block
- 3-4 blue-outlined flow boxes, such as pain, fit, cost, decision
- compact 30-second version

Put the actual explanation inside the diagram. Do not create empty boxes with only arrows. The blue-outlined boxes are for the interviewer's decision framework; the black/dark-gray outlined areas are for the candidate's speakable script.

When Excalidraw MCP tools are available:

1. Call `read_me` once if tool usage is unclear.
2. Create one board with `create_view`.
3. Export it with `export_to_excalidraw`.
4. Generate or capture a preview image and show it directly in chat before the link.
5. Return the Excalidraw URL as the editable/openable backup.

Chat delivery rule:

- The final response should normally be only:
  1. the rendered preview image
  2. the Excalidraw URL or `.excalidraw` file path
- Display the rendered Excalidraw preview image directly in the response using Markdown image syntax whenever possible.
- Put the Excalidraw URL or `.excalidraw` file path after the image as a backup, not as the primary way to inspect the output.
- Do not include the generated script text outside the visual unless the user explicitly asks for the text.
- If a preview image cannot be generated, return the link/path and briefly say the preview was unavailable.

For the JSON passed to `export_to_excalidraw`, use real Excalidraw `text` elements for editable text. Do not rely on MCP-only `label` shorthand inside shapes; it can display in the MCP preview but export to excalidraw.com as blank boxes. If using `label` for `create_view`, convert it into explicit text elements before export.

Chinese handwriting rule:

- Excalidraw's Virgil font may not provide handwritten CJK glyphs, so `fontFamily: 1` can still render Chinese as a plain fallback font.
- When the user wants Chinese to look handwritten, render Chinese text blocks as transparent PNG or SVG using a Chinese handwriting-style font, then embed them as Excalidraw `image` elements with `files` data URLs.
- Prefer `HanziPen SC` / `Hanzipen.ttc` when available on macOS. Fall back to `Kaiti`, `Yuanti`, or editable `fontFamily: 1` text only when no suitable Chinese handwriting font is available.
- When exporting a share link with image-rendered Chinese, make sure the image files are included in the `.excalidraw` `files` map and uploaded/saved with the share link; otherwise excalidraw.com can open the board with blank image placeholders.
- Keep the original Chinese script in the chat response because image-rendered Chinese in Excalidraw is not directly editable as text.

Use a simple top-to-bottom layout: script block first, blue decision flow second, 30-second version last. Keep text readable and non-overlapping. Chinese labels and script are the default for diagrams unless the user asks for English-only.

Visual spacing rules:

- Use generous padding: at least 32 px inside large script cards and 24 px inside flow boxes.
- Use comfortable line spacing: `lineHeight` around 1.35-1.5 for script text and 1.25-1.35 for short labels.
- Prefer fewer wider text lines over dense paragraphs. Add manual line breaks where needed.
- Keep 40-60 px vertical gaps between major sections.
- Use Excalidraw's handwritten roughness/hand-drawn feel; set editable text `fontFamily: 1`, use roughness around `1.5-2`, keep rectangle backgrounds transparent, and make the board feel like an Excalidraw note, not a slide deck.

When Excalidraw MCP tools are not available:

1. Create a `.excalidraw` artifact when filesystem access is available.
2. Return the absolute file path.
3. Output an **Excalidraw Board Brief** only if neither MCP export nor file creation is possible.

## Style Rules

- Be concise and speakable.
- Put the summary and script inside the visual; do not lead the chat response with copied script text by default.
- Always include a direct preview image when possible, plus an Excalidraw URL or file path as backup.
- Use the user's examples when present; add only one small realistic example when needed.
- Do not over-explain basic definitions.
- Keep Chinese and English aligned in substance, but let each sound natural.
- Do not add broad interview advice unless asked.
- Use code-style formatting for endpoints, methods, fields, commands, and identifiers.

## Example Shape

For an API design excerpt:

"中文: 这个问题我会先判断这个值是在定位资源，还是只是在过滤结果。如果没有这个值，请求本身就不成立，我会把它放在 path；如果它只是缩小集合范围，我会放在 query parameter。这样 API contract 会更清楚，客户端也更容易理解哪些字段是必需的。"

"English: I would first decide whether the value identifies the resource or only filters a collection. If the request does not make sense without it, it belongs in the path; if it only narrows results, it belongs in query parameters. That keeps the API contract clear for clients."
