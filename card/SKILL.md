---
name: card
description: "Turn pasted text, article excerpts, study notes, interview topics, system design/API notes, or explanation requests into diagram-first Excalidraw visuals with concise embedded talk tracks. Use when the user says use $card, make a card, draw an Excalidraw card, create a visual explanation, summarize this into a visual note, prepare an interview answer, or wants a short explainable version of arbitrary text. Prefer dynamic diagrams, decision trees, comparisons, pipelines, concept maps, architecture-style blocks, and callouts over long article-like script blocks."
---

# Card

## Goal

Create an Excalidraw whiteboard visual explanation, not a rewritten article. The board should feel like a hand-drawn technical whiteboard: task/constraints at the top, native Excalidraw blocks in the middle, arrows that show relationships, and sticky notes for gotchas, caveats, or production implications.

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
- Use callouts for gotchas, caveats, failure modes, and production implications.
- Keep any talk track short, usually 3-5 lines. Prefer returning it in chat when the user wants copyable speaking notes.
- Prefer concrete labels over generic labels like "Core idea" or "Tradeoff".
- Avoid decorative component icons by default; they often steal width from the sentence and can destabilize layout.
- Prefer one sentence per line when it fits. Do not manually break one sentence into many short fragments.
- Do not use the old `summary + long script + four flow boxes` layout.

## Board Content Vs Talk Track

For interview or technical-learning material, do not summarize the paragraph mechanically. First infer what an excellent candidate would understand, then separate the output into two layers:

1. **Board content**: what the candidate would actually draw on the whiteboard. This must be professional design content: entities, decisions, constraints, mechanisms, tradeoffs, and failure modes.
2. **Talk track**: what the candidate would say while pointing at the board. This can use first person and interview phrasing.

The board must not sound like interview coaching. Avoid phrases like `I would`, `my decision rule`, `interview signal`, `面试可讲`, `我会`, `我的判断`, or `面试里` inside `task`, `constraints`, `blocks`, `connectors`, or `callouts`. Put those in `talk_track` only.

Before writing the JSON, mentally produce this content plan:

1. **Whiteboard objective**: the concrete design question or concept being solved.
2. **Board blocks**: professional labels and compact design statements.
3. **Mechanisms**: what technique, storage choice, protocol, or data flow implements the decision.
4. **Tradeoffs**: latency, consistency, retry behavior, operational cost, failure mode, or product implication.
5. **Talk track**: 60-90 seconds when requested, written as direct candidate language.

The visual blocks should contain **design sentence density**, not keyword density. A good board block sounds like this:

```text
CP for expensive wrong state
Inventory, payment, and seat holds cannot confirm stale state.
Use conditional writes, transactions, or strong reads; degrade instead of accepting double booking.
```

Avoid blocks like this:

```text
CP
Strong consistency
Transactions
RDBMS
```

Use this block formula by default:

- `title`: decision, mechanism, or design boundary in 3-8 words.
- `body`: 2-3 compact design sentences. Include what it does and why it changes the architecture.
- `callout`: gotcha, tradeoff, production caveat, or product implication.

The board can still be concise, but it should look like a strong candidate's actual whiteboard, not notes about how to answer.

## Choose A Layout

Pick the layout that fits the source:

- `comparison`: for CP vs AP, REST vs GraphQL, offset vs cursor, Redis vs DB.
- `architecture`: for services, data stores, caches, clients, system boundaries, and API/RPC flows.
- `pipeline`: for request flows, async processing, replication, CDC, queues.
- `concept-map`: for explaining one concept through surrounding causes, examples, caveats, and implications.
- `auto`: only when none of the above clearly fits.

Use manual `x`, `y`, `width`, and `height` when a custom layout would explain the idea better. Coordinates are pixels on a roughly `1760px` wide canvas. Prefer fewer clean arrows over dense crossing arrows; use callouts for side notes.

## Excalidraw+ Alignment

Treat the Excalidraw+ docs as the visual source of truth: diagrams should be native scene content, not screenshots of an article. The renderer creates native block and connector elements and attaches semantic metadata so it can route and validate the scene.

Hard visual rules:

- Text must fit inside its parent block. If content is important, increase the block height instead of letting text escape.
- Arrows and connector lines must not pass through unrelated blocks. Move blocks or let the renderer route around obstacles.
- Connector labels should sit beside lines and avoid blocks; keep labels short.
- Prefer clean block placement over manual point hacks. Use explicit `points` only when a custom route is truly clearer.
- Decorative vector icons are opt-in only with `show_icon: true`.

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
      "title": "CP for expensive wrong state",
      "body": "Inventory, payment, and seat holds cannot confirm stale state. Use conditional writes, transactions, or strong reads; degrade instead of accepting double booking."
    },
    {
      "id": "ap",
      "lane": "right",
      "kind": "component",
      "title": "AP for freshness-as-UX",
      "body": "Browsing, feeds, and recommendations can tolerate short-lived stale data. Serve from replicas or cache, then converge asynchronously."
    }
  ],
  "connectors": [
    {"from": "cp", "to": "ap", "label": "same partition, different product priority"}
  ],
  "callouts": [
    {
      "title": "Partition-time choice",
      "body": "Once a network partition exists, the practical tradeoff is stale reads versus failed requests."
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
- Do not add `icon` by default. If a specific icon is truly needed, set both `icon` and `show_icon: true`; otherwise let the block shape and title carry the meaning.
- Keep each block to 2-4 short whiteboard lines; use dynamic height rather than deleting the reasoning.
- Keep each sentence intact on one line when width allows. Let wrapping happen only as a fallback for genuinely long sentences.
- Make every block earn its place: no empty labels, no generic filler.
- Do not reduce interview material to bare keywords. Every block should answer "what this design element does" or "what tradeoff it introduces".

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
- Pale yellow/pink/mint fills for sticky notes, caveats, and production notes.
- Dashed rounded frames for `Task:` and `Constraints:`.
- Handwritten Excalidraw feel, including Chinese when requested.
- Rows should use the available width and align cleanly at the left/right edges when possible.
- Left-align block body text by default; center only titles or tiny actor/client nodes when it improves scanning.
- Readable line breaks: prefer sentence-level lines over phrase fragments.
- Never accept a rendered scene where text escapes a block or an arrow crosses through a block.

## Quality Bar

- Make the picture explain the idea before the talk track is read.
- Convert paragraphs into relationships: choices, causes, consequences, examples, and failure modes.
- For technical interview content, show senior judgment through tradeoffs, production implications, and boundary conditions.
- If the output still looks like a long essay with a small flowchart, revise the JSON before rendering.
