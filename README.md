# Senior SDE Interview Script Skill

A Codex skill for turning technical interview excerpts into speakable senior SDE interview answers.

The skill produces bilingual Chinese and English output by default:

- one-sentence summaries in Chinese and English
- a Chinese speakable interview answer
- an English speakable interview answer
- 30-second versions in both languages
- optional bilingual follow-up prep for senior-level tradeoffs and edge cases

## Install

In Codex, install it from this GitHub path with `$skill-installer`:

```text
Use $skill-installer to install https://github.com/danielwanwx/senior-sde-interview-script-skill/tree/main/senior-sde-interview-script
```

Or copy the skill folder into your local Codex skills directory:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/danielwanwx/senior-sde-interview-script-skill.git /tmp/senior-sde-interview-script-skill
cp -R /tmp/senior-sde-interview-script-skill/senior-sde-interview-script ~/.codex/skills/
```

Then start a new Codex session and invoke:

```text
Use $senior-sde-interview-script to turn this technical excerpt into bilingual senior SDE interview scripts.
```

## 中文说明

这个 Codex skill 会把技术面试材料转换成 senior SDE candidate 可以直接讲的中英文面试底稿。

默认输出包括：

- 中文和英文一句话总结
- 中文可直接讲版本
- 英文可直接讲版本
- 中英文 30 秒短版
- 必要时补充中英文追问准备
