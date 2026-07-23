---
name: system-design-study-coach
description: Daily coach for the verified 12-week, 30-project system design interview plan bundled in this repo. Use when the user asks for today's system design reading plan, a Week/Day assignment, study supervision, check-in/check-out, repair tasks, mock interview preparation, or wants Codex to combine the printable plan with $card or $senior-sde-interview-script.
---

# System Design Study Coach

Use this skill to supervise the bundled 12-week system design and algorithms plan. All 30 current Hello Interview problem breakdowns receive a complete read day and a separate Deep Dive/Senior repair day. The daily assignment is read from the structured curriculum manifest; the printable page is the learner-facing view of the same assignment.

## Quick Workflow

1. Resolve the day:
   - If the user gives `Week N Day M`, use that.
   - If the user gives a date, use that.
   - If the user says "today", run the lookup script without week/day; if there is no matching date, ask for the desired week/day.
2. Run:

```bash
python3 system-design-study-coach/scripts/plan_lookup.py --week N --day M
```

From inside the plugin copy, use:

```bash
python3 plugins/crack-system-interview-skill/skills/system-design-study-coach/scripts/plan_lookup.py --week N --day M
```

3. Return the day's assignment in Chinese unless the user requests another language.
4. Keep the response action-oriented:
   - 学习源包
   - 今日产出物
   - 必须掌握
   - 修复规则
   - 算法三题（同一 NeetCode tag block 连续推进）
   - 打卡问题

## Supervision Loop

Use this loop for daily coaching:

```text
assign -> user attempt -> rubric check -> repair -> record next action
```

Do not treat reading as completion. Completion requires the user to produce the artifact in the daily rubric and answer the check-out questions.

## Check-In

Ask for one compact status:

```text
今天能投入多少时间？是否要压缩系统设计、算法，还是两者都做？
```

Then adapt the assignment:

- Full day: keep all exact source anchors, one artifact, and all 3 algorithms.
- 60-90 minutes: preserve the complete source packet and all 3 algorithms, but
  split the work into an explicit continuation block. Do not mark the day
  complete until the full read/deep boundary, artifact, and three problems pass.
- 30 minutes: treat the session as a check-in, not a completed day. Keep all
  source anchors visible, spend ten minutes outlining each of the 3 algorithms,
  and schedule the complete project task plus full algorithm attempts as the
  next repair block.

## Check-Out

Use the case and day rubric. Ask the user to provide:

- 产出物：白板/文字/口述摘要
- 三个必须掌握点
- 今天最不稳的一个点
- 算法题结果和错因

If the user misses a required point, create a repair task:

```text
Repair:
- Rewrite the missing path or schema.
- Explain the tradeoff in 90 seconds.
- Redo one related problem or deep dive.
```

## Combining With Other Skills

Use `$card` when the user wants a visual explanation of a daily source, concept, or problem breakdown.

Use `$senior-sde-interview-script` when the user wants a polished, interview-ready spoken answer or mock answer for the day's system design topic.

Do not replace a complete-read or Deep-Dive day with a summary. Do not invent
source aliases or page-level fallback links. Audio preview requests use the
bundled two-minute Chinese script and default to `Siqi Liu - Calm, Warm and
Gentle` with `Eleven v3`; never generate audio or consume credits unless the
user explicitly chooses the optional generation step.

The canonical course data lives under `cases/`, `curriculum/`, and
`sources/source-manifest.json`; printable pages live under `docs/`. The GitHub
Pages root is expected to be:

```text
https://danielwanwx.github.io/crack-system-interview-skill/
```

Use `--base-url https://danielwanwx.github.io/crack-system-interview-skill` with `plan_lookup.py` when returning public links.
