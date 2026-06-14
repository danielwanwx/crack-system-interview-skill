---
name: senior-sde-interview-script
description: "Convert Hello Interview excerpts, system design notes, API design notes, or other technical interview material into senior SDE interview speaking scripts embedded in Excalidraw visuals, with screenshot-and-link-only chat replies by default. Use when the user provides source paragraphs and asks for a concise but solid speakable interview answer, memorization-friendly draft, English-default or multilingual output, Chinese/English bilingual version, 30-second version, Excalidraw diagram, or asks to preserve this response pattern. Also use when the user wants answers to sound senior, practical, opinionated, and interview-ready without becoming textbook-like, overly long, or overly autobiographical."
---

# Senior SDE Interview Script

## Overview

Turn technical source material into a short answer a senior SDE candidate can actually say in an interview, then map the same content into an Excalidraw visual. Preserve the source's intent, but do not try to cover every pasted detail. Pick the points an interviewer is likely testing.

## Core Output

Unless the user asks for a different structure, generate the following content for the Excalidraw board:

- **Target Language**: default to English. Use Chinese or another language only when the user explicitly requests it, for example "用中文", "Chinese", "Spanish", or "output in Japanese". If the user asks for bilingual output, include both requested languages.
- **One-Sentence Summary**: one short sentence in the target language explaining what the paragraph is about.
- **Interview Script**: 2 short paragraphs in the target language, suitable for a 90-120 second spoken answer.
- **Excalidraw Visual**: show a rendered preview image directly in chat whenever possible, and include a direct Excalidraw share link as the editable backup. The board must include the speakable script text, not just empty concept boxes. Chinese text should look handwritten too, not only English. If MCP export is not available, create a `.excalidraw` file and return the path. Use a Board Brief only as the last fallback.
- **30-Second Version**: one compact answer in the target language, at most two sentences.
- **Follow-Up Prep**: omit by default. Add only one short gotcha when it is highly likely to be asked or the user requests it.

Default chat reply must contain only the rendered preview image and the Excalidraw link or `.excalidraw` path. Do not repeat the summary, interview script, 30-second version, or follow-up text outside the image unless the user explicitly asks for copyable text.

## Workflow

1. Infer the likely interview question behind the excerpt.
2. Determine the target language: English by default; use a requested language when specified; use bilingual only when explicitly requested.
3. Start with one concise summary sentence in the target language.
4. Extract only 4-5 interview-useful points:
   - the decision rule
   - when to use it
   - one realistic example
   - one senior caveat or tradeoff
   - one production implication when it changes the decision
5. Reframe the material as a senior candidate evaluating a real design situation.
6. Add practical depth only when it changes the decision: retries, caching, authorization, consistency, client contracts, observability, or operational cost.
7. Create the Excalidraw visual as a hybrid script card with a blue decision flow and prefer a direct share link.
8. End with a crisp principle the candidate can remember.

## Length Budget

- Live answer in the target language: 90-120 seconds, usually 2 short paragraphs.
- 30-second version: max 2 sentences in the target language.
- Bilingual output: keep each language concise; do not double the length of the board unless the user explicitly asks for a full bilingual script.
- Follow-up prep: omit unless asked, or include exactly one obvious gotcha.
- Do not enumerate every detail from the excerpt. Show judgment, not coverage.

## Voice And Stance

Produce English by default. Switch to Chinese or another language only when the user explicitly requests it. If the user writes in Chinese but does not specify output language, still default to English unless the current conversation clearly established Chinese as the target language.

Use a candidate-owned point of view without sounding like a diary. Good English phrases:

- "I would first look at..."
- "My decision rule is..."
- "I would lean toward..."
- "In a real design, I would care about..."
- "The key is not...but..."

Good Chinese phrases when Chinese is requested:

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

Use the bundled renderer first when filesystem access is available. It is colocated with this `SKILL.md` at `scripts/render_interview_card.py` and keeps layout, CJK handwriting, transparent frames, preview generation, and Excalidraw sharing consistent across Codex, Cursor, and Claude Code. Excalidraw MCP is optional; use it only as an enhancement or fallback when the user explicitly wants live MCP drawing.

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
- large interview script block in the target language
- 3-4 blue-outlined flow boxes, such as pain, fit, cost, decision
- compact 30-second version

Put the actual explanation inside the diagram. Do not create empty boxes with only arrows. The blue-outlined boxes are for the interviewer's decision framework; the black/dark-gray outlined areas are for the candidate's speakable script.

Bundled renderer workflow:

1. Produce a compact content JSON object with this exact shape:

```json
{
  "title": "GraphQL",
  "language": "English",
  "summary": "One short sentence explaining the core interview idea.",
  "script": "A 90-120 second senior SDE interview answer in the target language, usually 2 short paragraphs.",
  "short": "A 30-second version in the target language, max 2 sentences.",
  "flows": [
    "Signal / pain",
    "When it fits",
    "Tradeoff",
    "Decision"
  ]
}
```

2. Run the renderer from the skill folder, using an absolute path if the current working directory is not the skill folder:

```bash
python3 scripts/render_interview_card.py --content /tmp/interview-card.json --out /tmp/interview-card --slug interview-card
```

3. Read the emitted result JSON from stdout. It contains `preview`, `excalidraw`, `link`, and `share`.
4. In Codex or Cursor, return exactly a Markdown image for `preview`, then the `link` if present, otherwise the `.excalidraw` path.
5. In Claude Code or any terminal-only host that cannot inline local images, return the `link` first. If no link is available, return the `preview` and `.excalidraw` paths. Do not paste the script text outside the image unless the user explicitly asks.

When Excalidraw MCP tools are available and the bundled renderer cannot be used:

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
- Keep the original target-language script in the content JSON and generated artifacts, but do not repeat it in the chat response by default.

Use a simple top-to-bottom layout: script block first, blue decision flow second, 30-second version last. Keep text readable and non-overlapping. English labels and script are the default for diagrams unless the user requests another language.

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
- For bilingual output, keep both languages aligned in substance, but let each sound natural.
- Do not add broad interview advice unless asked.
- Use code-style formatting for endpoints, methods, fields, commands, and identifiers.

## Example Shape

For an API design excerpt:

"English default: I would first decide whether the value identifies the resource or only filters a collection. If the request does not make sense without it, it belongs in the path; if it only narrows results, it belongs in query parameters. That keeps the API contract clear for clients."

"Chinese when requested: 这个问题我会先判断这个值是在定位资源，还是只是在过滤结果。如果没有这个值，请求本身就不成立，我会把它放在 path；如果它只是缩小集合范围，我会放在 query parameter。这样 API contract 会更清楚，客户端也更容易理解哪些字段是必需的。"
