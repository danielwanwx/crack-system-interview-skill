---
name: card
description: "Turn pasted text, article excerpts, study notes, interview topics, system design/API notes, or explanation requests into diagram-first Excalidraw visuals with concise embedded talk tracks. Use when the user says use $card, make a card, draw an Excalidraw card, create a visual explanation, summarize this into a visual note, prepare an interview answer, or wants a short explainable version of arbitrary text. Prefer dynamic diagrams, decision trees, comparisons, pipelines, concept maps, architecture-style blocks, and callouts over long article-like script blocks."
---

# Card

## Goal

Create an Excalidraw-style visual explanation, not a rewritten article. The diagram should help the user understand the idea by showing structure, decisions, contrasts, flow, causality, and tradeoffs. Keep the speakable script as a small support layer inside the visual.

Default to English unless the user specifies Chinese or another language.

## Output Contract

Default chat response:

1. Rendered preview image when the host can display it.
2. Excalidraw link if upload succeeds; otherwise the `.excalidraw` path.

Do not paste the script text outside the image unless the user asks for copyable text.

## Diagram-First Rule

Avoid the old pattern of `summary + long script + four boxes + short version`. That feels like moving an article into a card.

Instead:

- Make the visual structure the main explanation.
- Use multiple small blocks, each with one solid idea.
- Put reasoning on arrows when the transition matters.
- Use callouts for gotchas, caveats, interviewer signals, and production implications.
- Keep the final talk track short, usually 3-5 lines.
- Prefer concrete labels over generic labels like "Core idea" or "Tradeoff".

## Choose A Layout

Pick the layout that fits the source:

- `decision`: for "should we choose A or B?", interview tradeoffs, CAP, consistency vs availability.
- `comparison`: for CP vs AP, REST vs GraphQL, offset vs cursor, Redis vs DB.
- `pipeline`: for request flows, async processing, replication, CDC, queues.
- `architecture`: for services, data stores, caches, clients, and system boundaries.
- `concept-map`: for explaining one concept through surrounding causes, examples, caveats, and implications.
- `auto`: only when none of the above clearly fits.

Use manual `x`, `y`, `width`, and `height` when a custom layout would explain the idea better. Coordinates are pixels on a roughly `1760px` wide canvas. Prefer fewer clean arrows over dense crossing arrows; use callouts for side notes.

## Content Shape

Create a compact JSON object for the renderer:

```json
{
  "title": "CAP in Interviews",
  "language": "English",
  "layout": "decision",
  "summary": "CAP is a partition-time product decision: stale data or failed requests.",
  "blocks": [
    {
      "id": "partition",
      "kind": "decision",
      "title": "Partition happens",
      "body": "P is not optional in real distributed systems."
    },
    {
      "id": "cp",
      "kind": "option",
      "title": "Choose CP",
      "body": "Block/fail requests to avoid stale reads."
    },
    {
      "id": "ap",
      "kind": "option",
      "title": "Choose AP",
      "body": "Keep serving, tolerate temporary staleness."
    }
  ],
  "connectors": [
    {"from": "partition", "to": "cp", "label": "wrong data is expensive"},
    {"from": "partition", "to": "ap", "label": "downtime is expensive"}
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

Legacy fields `summary`, `script`, `short`, and `flows` still work, but prefer `blocks`, `connectors`, `callouts`, and `talk_track`.

## Block Guidance

- `kind: decision` renders as a diamond.
- `kind: option`, `concept`, `step`, `system`, or `data` renders as a blue outlined block.
- `kind: caveat`, `warning`, or `risk` renders as a warning callout.
- `kind: note`, `example`, or `talk_track` renders as a dark outlined note.
- `kind: client`, `actor`, or `user` can render as an ellipse in architecture diagrams.
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
- Transparent block backgrounds.
- Blue strokes/text/arrows for main diagram structure.
- Black/dark strokes for notes and talk track.
- Red only for real warnings or caveats.
- Handwritten Excalidraw feel.
- Generous spacing and readable line breaks.

## Quality Bar

- Make the picture explain the idea before the talk track is read.
- Convert paragraphs into relationships: choices, causes, consequences, examples, and failure modes.
- For technical interview content, show senior judgment through tradeoffs, production implications, and boundary conditions.
- If the output still looks like a long essay with a small flowchart, revise the JSON before rendering.
