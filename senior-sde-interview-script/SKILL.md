---
name: senior-sde-interview-script
description: Convert Hello Interview excerpts, system design notes, API design notes, or other technical interview material into concise bilingual Chinese and English senior SDE candidate speaking scripts that begin with one-sentence summaries of what the source paragraph is about. Use when the user provides source paragraphs and asks for a directly speakable interview answer, a memorization-friendly draft, a grounded practical explanation, bilingual Chinese/English versions, a 30-second version, follow-up prep, or asks to preserve this response pattern. Also use when the user wants answers to sound senior, solid, practical, and opinionated without becoming textbook-like or overly autobiographical.
---

# Senior SDE Interview Script

## Overview

Turn technical source material into bilingual Chinese and English interview answers that a senior SDE candidate can say out loud. Preserve the source's scope, add only enough practical framing to make the answer feel experienced, and avoid turning the response into abstract concept recitation.

## Core Output

Unless the user asks for a different structure, produce:

- **一句话总结 / One-Sentence Summary**: one sentence in Chinese and one sentence in English that state what the source paragraph is mainly about.
- **中文可直接讲的版本**: 2-5 concise Chinese paragraphs, suitable to speak in an interview.
- **English Speakable Version**: 2-5 concise English paragraphs with the same substance and senior-level stance, not a word-for-word translation if natural phrasing requires adjustment.
- **30 秒短版 / 30-Second Version**: one compact Chinese paragraph and one compact English paragraph for fast recall.
- **追问准备 / Follow-Up Prep**: optional, only when the excerpt naturally has senior-level edge cases or tradeoffs worth anticipating; keep it short and bilingual when included.

Do not add long explanations about the process. The user wants the answer draft, not a teaching essay about how it was produced.

## Workflow

1. Identify the likely interview question behind the excerpt.
2. Start the response with one concise Chinese sentence and one concise English sentence summarizing what the excerpt is about.
3. Extract the source's actual decision rules, examples, caveats, and vocabulary.
4. Reframe the material as answers from a senior SDE candidate evaluating a real design situation, first in Chinese and then in English.
5. Add practical depth only where it follows naturally: production retries, failure modes, API contracts, data consistency, observability, operational cost, client expectations, or tradeoffs.
6. Keep the answer scoped to the excerpt. Do not expand into a mini-lecture or introduce many unrelated topics.
7. End with a crisp principle or judgment standard the candidate can remember.

## Voice And Stance

Produce both Chinese and English by default. Put Chinese first unless the user explicitly asks otherwise.

Use a candidate-owned point of view, but not a full first-person autobiography. Prefer phrases like:

- "这个问题我会先看..."
- "我的判断标准是..."
- "我会倾向于..."
- "在实际设计里，我会关注..."
- "这里关键不是...而是..."

Avoid overusing "我在项目中..." or "当我遇到..." in every paragraph. The answer should sound like a senior candidate standing in front of the problem, making a clear judgment, and explaining why.

## Senior-Level Signal

Make the answer feel senior by including at least two of these when relevant:

- The design rule, not just the definition.
- Why the rule matters in production.
- A concrete API, data, or distributed-systems scenario.
- A tradeoff or boundary condition.
- A retry, failure, consistency, or client-contract implication.
- A short note about when not to use the pattern.

Keep the language plain. Do not stack buzzwords. Avoid "concept dump" answers that define terms but never say how to choose.

## Style Rules

- Be concise and speakable.
- Make the first line a one-sentence summary of the source paragraph's topic, not a meta-comment about the answer.
- Use the user's examples when present.
- Use realistic examples when they clarify the source, but keep them small.
- Do not over-explain basic definitions unless the excerpt depends on them.
- Produce both Chinese and English versions by default; keep both versions aligned in substance.
- Do not add broad interview advice unless asked.
- Use code-style formatting for endpoints, methods, fields, commands, and identifiers.

## Example Shape

For an API design excerpt, the main answer should sound like:

"中文: 这个问题我会先判断这个值是在定位资源，还是只是在过滤结果。如果没有这个值，请求本身就不完整，我会把它放在 path 里；如果它只是缩小集合范围，我会放在 query parameter 里。比如..."

"English: I would first decide whether the value identifies the resource or only filters the result set. If the request does not make sense without it, I would put it in the path; if it only narrows a collection, I would use a query parameter. For example..."

Then connect it to a practical consequence, such as client clarity, API stability, retries, authorization checks, or avoiding over-nesting.
