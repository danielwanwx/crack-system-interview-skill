---
name: senior-sde-interview-script
description: "Convert Hello Interview excerpts, system design notes, API design notes, or other technical interview material into senior SDE interview-ready, diagram-first Excalidraw visuals with concise embedded talk tracks. Use when the user provides source paragraphs and asks for a concise but solid speakable interview answer, memorization-friendly draft, English-default or multilingual output, Chinese/English bilingual version, 30-second version, Excalidraw diagram, or asks to preserve this response pattern. Also use when the user wants answers to sound senior, practical, opinionated, and interview-ready without becoming textbook-like, overly long, or overly autobiographical."
---

# Senior SDE Interview Script

## Goal

Turn technical source material into a visual explanation a senior SDE candidate could use in an interview. The output should feel like an Excalidraw whiteboard: structure, tradeoffs, decision rules, gotchas, and a small embedded talk track. Do not turn the source into a long article card.

Default to English unless the user explicitly asks for Chinese or another language.

## Output Contract

Default chat response:

1. Rendered preview image when the host can display it.
2. Excalidraw link if upload succeeds; otherwise the `.excalidraw` path.

Do not paste the script text outside the image unless the user asks for copyable text.

## Senior Interview Shape

Start with one sentence summarizing what the excerpt is really about. Then build the visual around the ideas an interviewer is likely testing:

- decision rule
- when to use it
- realistic system/API example
- tradeoff or failure mode
- senior caveat
- production implication when it changes the design

The board should explain the topic before the talk track is read. The talk track should be short, usually 3-5 lines, and sound like a candidate making a judgment, not a textbook reciting definitions.

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

- `decision`: CAP, consistency vs availability, REST vs GraphQL choice, sync vs async.
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
      "body": "Block or fail requests to avoid stale reads."
    },
    {
      "id": "ap",
      "kind": "option",
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

Legacy fields `summary`, `script`, `short`, and `flows` still work, but prefer `blocks`, `connectors`, `callouts`, and `talk_track`.

## Block Guidance

- `kind: decision` renders as a diamond.
- `kind: option`, `concept`, `step`, `system`, or `data` renders as a blue outlined block.
- `kind: caveat`, `warning`, or `risk` renders as a red warning callout.
- `kind: note`, `example`, or `talk_track` renders as a dark outlined note.
- `kind: client`, `actor`, or `user` can render as an ellipse in architecture diagrams.
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
- Transparent block backgrounds.
- Blue strokes/text/arrows for the main diagram structure.
- Black/dark strokes for notes, examples, and the talk track.
- Red only for real warnings or caveats.
- Handwritten Excalidraw feel, including Chinese when requested.
- Generous spacing and readable line breaks.

## Quality Bar

- One sentence summary first, then a diagram-first explanation.
- No long pasted script block unless the user explicitly asks for copyable text.
- Convert paragraphs into relationships: choices, causes, consequences, examples, and failure modes.
- Show senior judgment through tradeoffs, production implications, and boundary conditions.
- If the board still looks like a long essay with a tiny flowchart, revise the JSON before rendering.
