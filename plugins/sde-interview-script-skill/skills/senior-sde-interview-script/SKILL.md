---
name: senior-sde-interview-script
description: "Convert Hello Interview excerpts, system design notes, API design notes, or other technical interview material into senior SDE interview-ready, diagram-first Excalidraw visuals with concise embedded talk tracks. Use when the user provides source paragraphs and asks for a concise but solid speakable interview answer, memorization-friendly draft, English-default or multilingual output, Chinese/English bilingual version, 30-second version, Excalidraw diagram, or asks to preserve this response pattern. Also use when the user wants answers to sound senior, practical, opinionated, and interview-ready without becoming textbook-like, overly long, or overly autobiographical."
---

# Senior SDE Interview Script

## Goal

Turn technical source material into a visual explanation a senior SDE candidate could use in an interview. The output should feel like a real Excalidraw system-design whiteboard: task/constraints at the top, native blocks in the middle, arrows for relationships, and sticky notes for gotchas, caveats, or production implications. Do not turn the source into a long article card.

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

The board should explain the topic before the talk track is read. The board itself should look like a strong candidate's live whiteboard, not coaching notes about how to answer. If included, the talk track should be short, usually 3-5 lines, and sound like a candidate making a judgment, not a textbook reciting definitions.

## Board Content Vs Talk Track

This skill is not a keyword summarizer. Treat the source paragraph as raw material for a senior-candidate answer, but separate what goes on the board from what the candidate says aloud.

- **Board content**: professional design artifacts: resources, APIs, services, data flows, consistency boundaries, retry behavior, failure modes, and tradeoffs.
- **Talk track**: candidate speech. This can use first person and interview phrasing.

Do not put interview coaching phrases into the board JSON. Avoid `I would`, `my judgment`, `interview signal`, `candidate`, `面试可讲`, `我会`, `我的判断`, or `面试里` inside `task`, `constraints`, `blocks`, `connectors`, or `callouts`. Use those only in `talk_track` or in chat when the user asks for copyable speaking notes.

## Source Sufficiency And Auto Completion

Before creating the board JSON, classify the source:

- `complete`: the excerpt already contains enough mechanism, tradeoff, example, and caveat material for a senior answer.
- `partial`: the excerpt has the core idea but misses one or two points a strong candidate would naturally mention.
- `thin`: the user provided only a title, short prompt, or incomplete fragment.

Default behavior is automatic completion based on the content. Do not ask for more text unless the topic is ambiguous enough that any completion would likely be wrong.

Completion rules:

- For stable system-design or API-design knowledge, use model background to fill only the missing senior-level points.
- For current, niche, version-specific, product-specific, legal, medical, financial, or otherwise time-sensitive facts, use browsing or available trusted tools when the host allows it.
- Prefer primary or authoritative sources when browsing is used.
- Keep completion bounded: add at most 2-4 missing mechanisms, examples, caveats, or production implications.
- Do not turn the answer into a textbook. The board should stay concise and interview-usable.
- If a point is inferred rather than present in the source, keep it conservative and avoid implying it came from the pasted text.

When the source is partial or thin, include compact metadata in the JSON:

```json
"source_notes": {
  "completeness": "thin",
  "completion_mode": "model_background",
  "added_points": ["write amplification", "read amplification", "production fit"],
  "uncertain_points": []
}
```

Use `completion_mode: "none"` for complete sources, `"model_background"` for stable background completion, and `"researched"` when browsing or external tools were used. Keep `source_notes` out of the visual unless the user asks for citations or audit detail.

Before creating the board JSON, infer and write from this internal structure:

1. **Whiteboard objective.** The concrete design question being solved.
2. **Professional board blocks.** Decisions, mechanisms, and boundaries that can stand on a live system-design whiteboard.
3. **Judgment chain.** 2-4 blocks that each explain what design choice exists, why it matters, and what mechanism follows.
4. **Senior caveat.** One failure mode, operational cost, retry/idempotency issue, consistency boundary, caching caveat, or product implication.
5. **Speakable answer.** If requested outside the image, produce a 60-90 second answer in the requested language.

Also do a compact pre-drawing planning pass before choosing the final layout:

- Use `single`, `comparison`, `pipeline`, `architecture`, or `concept-map` when the excerpt is one clear idea.
- Use `modular-composite` when the excerpt has more than five meaningful entities, more than two flows, multiple technical types, or mixes architecture, consistency, scaling, and failure recovery.
- Split complex systems into modules such as overview, read path, write path, consistency boundary, async processing, failure recovery, or operational tradeoffs.
- Keep module names and blocks as professional whiteboard content, not interview coaching.

The visual text should have **design sentence density**. Good board block:

```text
Cursor pagination for shifting data
Offset pages can duplicate or skip records as new rows arrive.
Return a cursor tied to the last stable record for high-volume or real-time feeds.
```

Weak block:

```text
Cursor
Stable
High volume
```

Default block formula:

- `title`: a decision phrase, not a noun label.
- `body`: 2-3 short whiteboard sentences that explain mechanism and tradeoff.
- `callout`: one gotcha, product implication, or production caveat.

If a block feels like flashcard keywords, rewrite it into professional whiteboard content before rendering. Put candidate phrasing in `talk_track`, not in the block.

## Voice

Use a candidate-owned point of view in `talk_track` or chat explanations without sounding like a diary.

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
- `concept-map`: one concept with causes, examples, caveats, and production implications.
- `modular-composite`: larger system-design material that needs multiple coordinated mini-diagrams instead of one crowded workflow.
- `auto`: only when none of the above clearly fits.

Use manual `x`, `y`, `width`, and `height` when a custom layout would explain the idea better. Prefer fewer clean arrows over dense crossing arrows; use callouts for side notes.

Avoid decorative component icons by default. They are optional, and in dense interview boards they often reduce text width or cause layout drift. Prefer clean native blocks with strong labels and sentence-level content.

## Excalidraw+ Alignment

Treat the Excalidraw+ docs as the visual source of truth: the board should be native scene content, not article text disguised as a diagram. The renderer creates native block and connector elements and attaches semantic metadata so it can route and validate the scene locally; hosts with Excalidraw+ MCP can adapt the same structure to `edit_scene_content`.

Hard visual rules:

- Text must fit inside its parent block. If content matters, increase block height instead of clipping or spilling text.
- Arrows and connector lines must not pass through unrelated blocks. Reposition blocks or rely on obstacle-aware routing.
- Arrows should leave and enter block edges perpendicularly with short port stubs. Avoid routes that skim alongside a block edge or run parallel against the border before entering.
- Connector labels should feel attached to the line: keep them close to the stroke, slightly offset for readability, and move them farther only when needed to avoid blocks.
- Leave bottom breathing room on the whiteboard so the lowest block is fully visible in SVG previews and chat screenshots.
- Prefer block movement and right-angle routing over dense crossing arrows.
- Decorative vector icons are opt-in only with `show_icon: true`.

## Content Shape

Create a compact JSON object for the bundled renderer:

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
    {"from": "partition", "to": "cp", "label": "wrong data is costly"},
    {"from": "partition", "to": "ap", "label": "downtime is costly"}
  ],
  "callouts": [
    {
      "title": "Partition-time choice",
      "body": "Once a network partition exists, the practical tradeoff is stale reads versus failed requests."
    }
  ],
  "talk_track": "I would first ask which failure mode the product can tolerate: stale data or temporary unavailability."
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
- Do not add `icon` by default. If a specific icon is truly needed, set both `icon` and `show_icon: true`; otherwise keep the layout text-first.
- Keep each block to 2-4 short whiteboard lines; let dynamic height preserve the reasoning.
- Prefer one sentence per line when it fits. Do not manually split one sentence into many short phrase lines.
- Make every block earn its place: no empty labels, no generic filler like "Core idea".
- Do not reduce interview material to bare keywords. Every block should answer "what this design element does" or "what tradeoff it introduces".

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
- Pale yellow/pink/mint fills for sticky notes, caveats, and production notes.
- Dashed rounded frames for `Task:` and `Constraints:`.
- Handwritten Excalidraw feel, including Chinese when requested.
- Rows should use the available width and align cleanly at the left/right edges when possible.
- Left-align block body text by default; center only titles or tiny actor/client nodes when it improves scanning.
- Readable line breaks: prefer sentence-level lines over phrase fragments.
- Never accept a rendered scene where text escapes a block, an arrow crosses through a block, an arrow visually hugs a block border instead of entering perpendicularly, or the lowest row is cropped by the preview.

## Quality Bar

- One sentence summary first, then a diagram-first explanation.
- No long pasted script block unless the user explicitly asks for copyable text.
- Convert paragraphs into relationships: choices, causes, consequences, examples, and failure modes.
- Show senior judgment through tradeoffs, production implications, and boundary conditions.
- If the board still looks like a long essay with a tiny flowchart, revise the JSON before rendering.
