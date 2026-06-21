---
name: senior-sde-interview-script
description: "Convert Hello Interview excerpts, system design notes, API design notes, or other technical interview material into senior SDE interview-ready, diagram-first Excalidraw visuals with concise embedded talk tracks. Use when the user provides source paragraphs and asks for a concise but solid speakable interview answer, memorization-friendly draft, English-default or multilingual output, Chinese/English bilingual version, 30-second version, Excalidraw diagram, or asks to preserve this response pattern. Also use when the user wants answers to sound senior, practical, opinionated, and interview-ready without becoming textbook-like, overly long, or overly autobiographical."
---

# Senior SDE Interview Script

## Goal

Turn technical source material into a visual explanation a senior SDE candidate could use in an interview. The output should feel like an Excalidraw interview whiteboard: task/constraints at the top, native blocks in the middle, arrows for relationships, and sticky notes for gotchas or interviewer prompts. Do not turn the source into a long article card.

Default to English unless the user explicitly asks for Chinese or another language.

## Output Contract

Default chat response:

1. Rendered preview image when the host can display it.
2. Excalidraw link if upload succeeds; otherwise the `.excalidraw` path.

Do not paste the script text outside the image unless the user asks for copyable text. If the user asks for a speakable script, put it in chat and keep the board diagram-first.

## Senior Interview Shape

Start with one sentence summarizing what the excerpt is really about. Then build the visual around the ideas an interviewer is likely testing:

- decision rule
- when to use it
- realistic system/API example
- tradeoff or failure mode
- senior caveat
- production implication when it changes the design

The board should explain the topic before the talk track is read. If included, the talk track should be short, usually 3-5 lines, and sound like a candidate making a judgment, not a textbook reciting definitions.

## Voice

Use a candidate-owned point of view without sounding like a diary.

Good English phrases:

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

Avoid repeating "我在项目中..." or "当我遇到..." in every paragraph.

## Choose A Layout

Pick the layout that matches the concept:

- `comparison`: GraphQL vs REST, offset vs cursor, RPC vs REST, CP vs AP.
- `pipeline`: request flow, retry flow, booking/payment/inventory flow, CDC, replication.
- `architecture`: clients, gateways, services, databases, queues, caches, internal RPC.
- `concept-map`: one concept with causes, examples, caveats, and interview signals.
- `auto`: only when none of the above clearly fits.

Use manual `x`, `y`, `width`, and `height` when a custom layout would explain the idea better. Prefer fewer clean arrows over dense crossing arrows; use callouts for side notes.

## Content Shape

Create a compact JSON object for the bundled renderer:

```json
{
  "title": "CAP in Interviews",
  "language": "English",
  "style": "excalidraw-plus",
  "layout": "comparison",
  "summary": "CAP is a partition-time product decision: stale data or failed requests.",
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
      "icon": "database",
      "title": "Choose CP",
      "body": "Block or fail requests to avoid stale reads."
    },
    {
      "id": "ap",
      "lane": "right",
      "kind": "component",
      "icon": "cache",
      "title": "Choose AP",
      "body": "Keep serving and tolerate temporary staleness."
    }
  ],
  "connectors": [
    {"from": "partition", "to": "cp", "label": "wrong data is costly"},
    {"from": "partition", "to": "ap", "label": "downtime is costly"}
  ],
  "callouts": [
    {
      "title": "Interview signal",
      "body": "Do not mechanically say pick any two. During a partition, pick C or A."
    }
  ],
  "talk_track": "I would first ask which failure mode the product can tolerate: stale data or temporary unavailability."
}
```

Legacy fields `summary`, `script`, `short`, and `flows` still work, but prefer `style: "excalidraw-plus"`, `task`, `constraints`, `blocks`, `connectors`, and `callouts`.

## Block Guidance

- Use native Excalidraw shapes: `shape: "rectangle"`, `"square"`, `"circle"`, or `"ellipse"`.
- `kind: component`, `service`, `api`, `database`, `cache`, `queue`, or `storage` renders as a light-blue component block.
- `kind: note`, `callout`, or `question` renders as a sticky-note block.
- `kind: caveat`, `warning`, or `risk` renders as a yellow gotcha note.
- `kind: client`, `actor`, or `user` can render as a circle/ellipse in architecture diagrams.
- Add `icon: "api"`, `"database"`, `"cache"`, `"queue"`, `"storage"`, `"client"`, or `"service"` when it helps the block scan like a system-design whiteboard.
- Keep each block to 1-3 short lines.
- Make every block earn its place: no empty labels, no generic filler like "Core idea".

## Rendering

Use the bundled renderer first:

```bash
python3 scripts/render_interview_card.py --content /tmp/interview-card.json --out /tmp/interview-card --slug interview-card
```

If the current working directory is not this skill directory, run the script with its absolute path. Read the JSON emitted by the script; it contains `preview`, `excalidraw`, `link`, and `share`.

Host-specific delivery:

- Codex/Cursor: return Markdown image for `preview`, then `link` or `.excalidraw` path.
- Claude Code or terminal-only hosts: return `link` first; if no link exists, return `preview` and `.excalidraw` paths.

## Visual Style

- White background.
- Native Excalidraw block vocabulary: rounded rectangles, squares, circles/ellipses, dashed containers, arrows, and sticky notes.
- Black/dark strokes and arrow lines by default.
- Light-blue component fills (`#a5d8ff`) for main blocks.
- Pale yellow/pink/mint fills for sticky notes and interviewer prompts.
- Dashed rounded frames for `Task:` and `Constraints:`.
- Handwritten Excalidraw feel, including Chinese when requested.
- Generous spacing and readable line breaks.

## Quality Bar

- One sentence summary first, then a diagram-first explanation.
- No long pasted script block unless the user explicitly asks for copyable text.
- Convert paragraphs into relationships: choices, causes, consequences, examples, and failure modes.
- Show senior judgment through tradeoffs, production implications, and boundary conditions.
- If the board still looks like a long essay with a tiny flowchart, revise the JSON before rendering.
