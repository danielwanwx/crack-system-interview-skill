---
name: card
description: "Turn pasted text, article excerpts, study notes, interview topics, system design/API notes, or explanation requests into diagram-first Excalidraw visuals with concise embedded talk tracks. Use when the user says use $card, make a card, draw an Excalidraw card, create a visual explanation, summarize this into a visual note, prepare an interview answer, or wants a short explainable version of arbitrary text. Prefer dynamic diagrams, decision trees, comparisons, pipelines, concept maps, architecture-style blocks, and callouts over long article-like script blocks."
---

# Card

## Goal

Create an Excalidraw whiteboard visual explanation, not a rewritten article. The board should feel like a hand-drawn interview whiteboard: task/constraints at the top, native Excalidraw blocks in the middle, arrows that show relationships, and sticky notes for gotchas or interviewer prompts.

Default to English unless the user specifies Chinese or another language.

## Output Contract

Default chat response:

1. Rendered preview image when the host can display it.
2. Excalidraw link if upload succeeds; otherwise the `.excalidraw` path.

Do not paste the script text outside the image unless the user asks for copyable text. For interview prep, if the user asks for the speakable script separately, put that script in chat and keep the board diagram-first.

## Diagram-First Rule

Avoid the old pattern of `summary + long script + four boxes + short version`. That feels like moving an article into a card.

Instead:

- Make the visual structure the main explanation.
- Use multiple small blocks, each with one solid idea.
- Put reasoning on arrows when the transition matters.
- Use callouts for gotchas, caveats, interviewer signals, and production implications.
- Keep any talk track short, usually 3-5 lines. Prefer returning it in chat when the user wants copyable speaking notes.
- Prefer concrete labels over generic labels like "Core idea" or "Tradeoff".
- Do not use the old `summary + long script + four flow boxes` layout.

## Choose A Layout

Pick the layout that fits the source:

- `comparison`: for CP vs AP, REST vs GraphQL, offset vs cursor, Redis vs DB.
- `architecture`: for services, data stores, caches, clients, system boundaries, and API/RPC flows.
- `pipeline`: for request flows, async processing, replication, CDC, queues.
- `concept-map`: for explaining one concept through surrounding causes, examples, caveats, and implications.
- `auto`: only when none of the above clearly fits.

Use manual `x`, `y`, `width`, and `height` when a custom layout would explain the idea better. Coordinates are pixels on a roughly `1760px` wide canvas. Prefer fewer clean arrows over dense crossing arrows; use callouts for side notes.

## Content Shape

Create a compact JSON object for the renderer:

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
      "body": "Block/fail requests to avoid stale reads."
    },
    {
      "id": "ap",
      "lane": "right",
      "kind": "component",
      "icon": "cache",
      "title": "Choose AP",
      "body": "Keep serving, tolerate temporary staleness."
    }
  ],
  "connectors": [
    {"from": "cp", "to": "ap", "label": "same partition, different product priority"}
  ],
  "callouts": [
    {
      "title": "Interview signal",
      "body": "Do not say pick any two. During a partition, pick C or A."
    }
  ],
  "talk_track": "I would first ask what failure is cheaper for the product: stale data or temporary unavailability."
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
- Make every block earn its place: no empty labels, no generic filler.

## Language Rules

- Default to English.
- Use Chinese when the user writes `Chinese`, `用中文`, `in chinese`, or clearly asks for Chinese output.
- Use any other requested language directly.
- For bilingual output, make the diagram mostly structural and keep text short.

## Rendering

Use the bundled renderer first:

```bash
python3 scripts/render_interview_card.py --content /tmp/card.json --out /tmp/card-output --slug card
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

- Make the picture explain the idea before the talk track is read.
- Convert paragraphs into relationships: choices, causes, consequences, examples, and failure modes.
- For technical interview content, show senior judgment through tradeoffs, production implications, and boundary conditions.
- If the output still looks like a long essay with a small flowchart, revise the JSON before rendering.
