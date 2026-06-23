---
name: card
description: "Help users digest difficult technical or interview material by turning pasted text, article excerpts, study notes, system design/API notes, or explanation requests into coherent Excalidraw whiteboard samples plus concise talk tracks. Use when the user says use $card, make a card, draw an Excalidraw card, create a visual explanation, summarize this into a visual note, prepare an interview answer, understand a hard technical topic, or wants a short explainable version of dense material. Prefer dynamic diagrams, decision trees, comparisons, pipelines, concept maps, architecture-style blocks, and callouts over long article-like script blocks."
---

# Card

## Goal

Help the user understand, digest, and rehearse difficult technical material. Create an Excalidraw whiteboard sample plus a concise talk track, not a rewritten article. The board should feel like a hand-drawn technical whiteboard that a candidate could use as a model in an interview: task/constraints at the top, native Excalidraw blocks in the middle, arrows that show relationships, and sticky notes for gotchas, caveats, or production implications.

This skill has three jobs:

1. Make hard material easier to understand.
2. Turn that understanding into interview-ready speaking notes.
3. Provide a whiteboard example the user can imitate when explaining the topic.

Default to English unless the user specifies Chinese or another language.

## Output Contract

Default chat response:

1. Rendered preview image when the host can display it.
2. Excalidraw link if upload succeeds; otherwise the `.excalidraw` path.
3. Copyable interview talk track when the source is interview prep, system design, API design, or technical study material.

When the user pastes a paragraph to test or validate the skill, treat that as a request for a complete output: preview image, editable link/path, and a concise speakable script in chat. Keep the board diagram-first, but do not make the user open the image just to copy the talk track.

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

## Coherence First

A board is successful only if a reader can follow it without reading the talk track. Before writing blocks, choose a single reading path:

1. **Mental model**: the one picture or analogy that makes the topic obvious.
2. **Concrete example**: a small realistic request, query, API call, or failure scenario.
3. **Why the naive approach breaks**: show the wrong shape, wrong boundary, wrong ordering, or wrong failure mode.
4. **Correct mechanism**: show how the better design changes the shape, boundary, ordering, or failure handling.
5. **Correctness / choice rule**: end with what still must be verified and when to choose this option.

Do not scatter accurate facts into disconnected blocks. If the user has to assemble the causal chain themselves, revise the board.

Use these visual patterns when they fit:

- **Shape mismatch**: when the core issue is that the query shape and index/data shape do not match. Example: geospatial radius search wants a circle, while separate lat/lng B-trees return strips or rectangles. Draw target shape -> wrong shape -> candidate explosion -> spatial index -> exact filter.
- **Boundary mismatch**: when correctness depends on one component owning a boundary. Example: inventory, payment, idempotency, authorization, or cache invalidation.
- **Time/path mismatch**: when the issue is ordering over time. Example: retries, pagination drift, CDC lag, replication, async processing.
- **Tradeoff fork**: when two valid choices optimize different failure modes. Example: CP vs AP, REST vs GraphQL, offset vs cursor.
- **Lifecycle**: when the mechanism is a sequence of states. Example: seat hold -> payment -> confirmation -> expiry.

For multidimensional search, proximity search, ranking, or filtering problems, prefer a storyboard over a loose concept map. Show:

- the user request shape,
- the naive index/query shape,
- why that shape over-fetches or misses the point,
- the candidate-reduction mechanism,
- the final exact correctness check.

## Board Content Vs Talk Track

For interview or technical-learning material, do not summarize the paragraph mechanically. First infer what an excellent candidate would understand, then separate the output into two layers:

1. **Board content**: what the candidate would actually draw on the whiteboard. This must be professional design content: entities, decisions, constraints, mechanisms, tradeoffs, and failure modes.
2. **Talk track**: what the candidate would say while pointing at the board. This can use first person and interview phrasing.

The board must not sound like interview coaching. Avoid phrases like `I would`, `my decision rule`, `interview signal`, `面试可讲`, `我会`, `我的判断`, or `面试里` inside `task`, `constraints`, `blocks`, `connectors`, or `callouts`. Put those in `talk_track` only.

## Source Sufficiency And Auto Completion

Before writing the board, classify the pasted source:

- `complete`: it already has the mechanism, tradeoffs, examples, and caveats needed for a solid visual.
- `partial`: it has the core idea but misses one or two important interview points.
- `thin`: it is only a title, a short prompt, or a fragment.

Default behavior is automatic completion based on the content. Do not ask the user to paste more unless the topic is ambiguous enough that any completion would likely be wrong.

Completion rules:

- For stable technical knowledge, use model background to fill only the missing pieces needed for a strong board and talk track.
- For current, niche, version-specific, product-specific, legal, medical, financial, or otherwise time-sensitive facts, use browsing or available trusted tools when the host allows it.
- Prefer primary or authoritative sources when browsing is used.
- Keep completion bounded: add at most 2-4 missing mechanisms, examples, caveats, or production implications.
- Do not turn completion into a long tutorial. The final board should still be a concise whiteboard.
- If a fact is inferred rather than present in the source, keep it conservative and avoid pretending it came from the pasted text.

When the source is partial or thin, include a compact metadata object in the JSON so future QA and host agents can see what happened:

```json
"source_notes": {
  "completeness": "partial",
  "completion_mode": "model_background",
  "added_points": ["write amplification", "read amplification", "production fit"],
  "uncertain_points": []
}
```

Use `completion_mode: "none"` for complete sources, `"model_background"` for stable background completion, and `"researched"` when browsing or external tools were used. Do not render `source_notes` on the board unless the user asks for citations or audit detail.

Before writing the JSON, mentally produce this content plan:

1. **Whiteboard objective**: the concrete design question or concept being solved.
2. **Mental model**: the simplest visual frame that makes the issue click.
3. **Board blocks**: professional labels and compact design statements.
4. **Mechanisms**: what technique, storage choice, protocol, or data flow implements the decision.
5. **Tradeoffs**: latency, consistency, retry behavior, operational cost, failure mode, or product implication.
6. **Talk track**: 60-90 seconds when requested, written as direct candidate language.

Also do a compact pre-drawing planning pass before choosing the final layout:

- Use `single`, `comparison`, `pipeline`, `architecture`, or `concept-map` when the source is one clear idea.
- Use `modular-composite` when the source has more than five meaningful entities, more than two flows, multiple technical types, or mixes architecture, consistency, scaling, and failure recovery.
- Split complex systems into modules such as overview, read path, write path, consistency boundary, async processing, failure recovery, or operational tradeoffs.
- Keep the board content professional, as if drawn by the candidate during the interview. Do not put coaching instructions in module names or blocks.

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
- `modular-composite`: for larger system-design material that needs multiple coordinated mini-diagrams instead of one crowded workflow.
- `auto`: only when none of the above clearly fits.

Use manual `x`, `y`, `width`, and `height` when a custom layout would explain the idea better. Coordinates are pixels on a roughly `1760px` wide canvas. Prefer fewer clean arrows over dense crossing arrows; use callouts for side notes.

## Excalidraw+ Alignment

Treat the Excalidraw+ docs as the visual source of truth: diagrams should be native scene content, not screenshots of an article. The renderer creates native block and connector elements and attaches semantic metadata so it can route and validate the scene.

Hard visual rules:

- Text must fit inside its parent block. If content is important, increase the block height instead of letting text escape.
- Arrows and connector lines must not pass through unrelated blocks. Move blocks or let the renderer route around obstacles.
- Arrows should leave and enter block edges perpendicularly with short port stubs. Avoid routes that skim alongside a block edge or run parallel against the border before entering.
- Connector labels should feel attached to the line: keep them close to the stroke, slightly offset for readability, and move them farther only when needed to avoid blocks.
- Connector labels are relationship hints, not sentences. Use the requested language, keep them to 1-3 short words, and avoid awkward untranslated English on Chinese boards.
- Use semantic fills, not decorative or random colors. The same `kind` must use the same fill across a board; choose `kind` intentionally because it controls both visual role and color.
- Leave bottom breathing room on the whiteboard so the lowest block is fully visible in SVG previews and chat screenshots.
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
  "planning": {
    "complexity": "medium",
    "diagram_strategy": "comparison",
    "reason": "The source is a CP versus AP tradeoff."
  },
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

For `modular-composite`, include `planning.modules` or top-level `modules`, then assign each block to a module:

```json
{
  "layout": "modular-composite",
  "modules": [
    {"id": "overview", "title": "System overview", "layout": "overview", "full_width": true},
    {"id": "booking", "title": "Booking/write path", "layout": "pipeline"},
    {"id": "inventory", "title": "Consistency boundary", "layout": "concept"}
  ],
  "blocks": [
    {"id": "gateway", "module": "overview", "kind": "api", "title": "Edge protects the sale", "body": "Authenticate, rate-limit, and attach idempotency before requests reach booking."},
    {"id": "hold", "module": "booking", "kind": "service", "title": "Create an expiring seat hold", "body": "Reserve the seat for a short TTL before charging. Expiry releases inventory without manual cleanup."},
    {"id": "inventory", "module": "inventory", "kind": "database", "title": "Inventory is the CP boundary", "body": "Use conditional writes or transactions so one seat cannot have two active holds."}
  ]
}
```

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
- Chinese should preserve the original meaning while sounding natural. Avoid stiff literal translations or rare terms that make the board harder to read.
- When a technical English term is clearer, keep it with a short Chinese explanation the first time: `false positive（误命中 / 多取的候选）`, `locality（相近的数据放得更近）`, `bounding box（外接矩形）`.
- Prefer plain Chinese verbs: `缩小候选集`, `多取了一批点`, `最后再算真实距离`, `先挡住重复请求`, `让读请求落到缓存`.
- Do not use a Chinese translation just because one exists if it makes the sentence less clear.

## Rendering

Use the bundled renderer first:

```bash
python3 scripts/render_interview_card.py --content /tmp/card.json --out /tmp/card-output --slug card
```

If the current working directory is not this skill directory, run the script with its absolute path. Read the JSON emitted by the script; it contains `preview`, `excalidraw`, `link`, and `share`.

Host-specific delivery:

- Codex/Cursor: return Markdown image for `preview`, then `link` or `.excalidraw` path, then the copyable talk track when present.
- Claude Code or terminal-only hosts: return `link` first; if no link exists, return `preview` and `.excalidraw` paths; then include the copyable talk track when present.

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
- Never accept a rendered scene where text escapes a block, an arrow crosses through a block, an arrow visually hugs a block border instead of entering perpendicularly, or the lowest row is cropped by the preview.

## Quality Bar

- Make the picture explain the idea before the talk track is read.
- A good board has one obvious path through it. It should not feel like a pile of correct but disconnected notes.
- Start with the strongest mental model, not with definitions. For geospatial search, the mental model is "circle vs strip/rectangle"; for retries it might be "same request replayed"; for CAP it is "partition-time choice".
- Convert paragraphs into relationships: choices, causes, consequences, examples, and failure modes.
- For technical interview content, show senior judgment through tradeoffs, production implications, and boundary conditions.
- If the output still looks like a long essay with a small flowchart, revise the JSON before rendering.
