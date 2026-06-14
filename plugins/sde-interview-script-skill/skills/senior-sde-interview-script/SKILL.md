---
name: senior-sde-interview-script
description: "Convert Hello Interview excerpts, system design notes, API design notes, or other technical interview material into short senior SDE interview speaking scripts plus direct Excalidraw visual links when possible. Use when the user provides source paragraphs and asks for a concise speakable interview answer, memorization-friendly draft, bilingual Chinese/English version, 30-second version, Excalidraw diagram, or asks to preserve this response pattern. Also use when the user wants answers to sound senior, solid, practical, and opinionated without becoming textbook-like, overly long, or overly autobiographical."
---

# Senior SDE Interview Script

## Overview

Turn technical source material into a short answer a senior SDE candidate can actually say in an interview, then map the same content into an Excalidraw visual. Preserve the source's intent, but do not try to cover every pasted detail. Pick the points an interviewer is likely testing.

## Core Output

Unless the user asks for a different structure, produce:

- **一句话总结 / One-Sentence Summary**: one short Chinese sentence and one short English sentence explaining what the paragraph is about.
- **中文面试版**: 1-2 short Chinese paragraphs, suitable for a 60-90 second spoken answer.
- **English Short Version**: one short English paragraph with the same judgment and examples, not a literal translation.
- **Excalidraw Visual**: return a direct Excalidraw share link when tools allow it. If not, create a `.excalidraw` file and return the path. Use a Board Brief only as the last fallback.
- **30 秒短版**: one compact Chinese answer, at most two sentences.
- **追问准备 / Follow-Up Prep**: omit by default. Add only one short gotcha when it is highly likely to be asked or the user requests it.

Do not add long explanations about the process. The user wants an interview answer and a visual, not study notes.

## Workflow

1. Infer the likely interview question behind the excerpt.
2. Start with one concise Chinese summary sentence and one concise English summary sentence.
3. Extract only 3-4 interview-useful points:
   - the decision rule
   - when to use it
   - one realistic example
   - one senior caveat or tradeoff
4. Reframe the material as a senior candidate evaluating a real design situation.
5. Add practical depth only when it changes the decision: retries, caching, authorization, consistency, client contracts, observability, or operational cost.
6. Create the Excalidraw visual and prefer a direct share link.
7. End with a crisp principle the candidate can remember.

## Length Budget

- Chinese live answer: max 2 short paragraphs.
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

When Excalidraw MCP tools are available:

1. Call `read_me` once if tool usage is unclear.
2. Create one board with `create_view`.
3. Export it with `export_to_excalidraw`.
4. Return the Excalidraw URL directly in the answer.

Use 4-6 blocks:

- interview question
- core rule
- when to use
- concrete example
- gotcha or tradeoff
- takeaway

Use a simple left-to-right or top-to-bottom layout. Connect blocks with arrows that show reasoning. Keep diagram labels very short; English labels are fine for diagrams unless the user asks for Chinese labels. Do not put paragraphs in the drawing.

When Excalidraw MCP tools are not available:

1. Create a `.excalidraw` artifact when filesystem access is available.
2. Return the absolute file path.
3. Output an **Excalidraw Board Brief** only if neither MCP export nor file creation is possible.

## Style Rules

- Be concise and speakable.
- First line must summarize the paragraph's topic, not describe the response format.
- Always include a direct Excalidraw URL or a file path when possible.
- Use the user's examples when present; add only one small realistic example when needed.
- Do not over-explain basic definitions.
- Keep Chinese and English aligned in substance, but let each sound natural.
- Do not add broad interview advice unless asked.
- Use code-style formatting for endpoints, methods, fields, commands, and identifiers.

## Example Shape

For an API design excerpt:

"中文: 这个问题我会先判断这个值是在定位资源，还是只是在过滤结果。如果没有这个值，请求本身就不成立，我会把它放在 path；如果它只是缩小集合范围，我会放在 query parameter。这样 API contract 会更清楚，客户端也更容易理解哪些字段是必需的。"

"English: I would first decide whether the value identifies the resource or only filters a collection. If the request does not make sense without it, it belongs in the path; if it only narrows results, it belongs in query parameters. That keeps the API contract clear for clients."
