# Interview Case Core 设计

## 目标

将仓库从“学习卡、口述脚本、静态计划的集合”收敛为一个系统设计面试训练闭环：

```text
Learn -> Design -> Speak -> Mock -> Repair
```

核心产物不是白板，而是可复用、可评分、可修复的 `Interview Case`。候选人完成的标准是：能在规定时间内把模糊题目转成可辩护的工程决策，并接住追问。

## 范围与非目标

- 覆盖 18 周课程、现有三项 skill 与 GitHub Pages。
- 保留 `$card`、`$senior-sde-interview-script`、`$system-design-study-coach` 三个入口，避免破坏既有用法。
- 不把三个 skill 合并为一个长而模糊的万能 prompt。
- 不在本阶段新增新的学习内容或替换现有课程主题；先统一内容模型和发布链路。

## Canonical Case

每个项目题、概念题或 mock 题由一份版本化的 case manifest 描述。最小字段：

```text
id, title, type, level, prompt
requirements: functional, non_functional, out_of_scope
estimates, api, entities, high_level_design
deep_dives: decision, alternatives, failure_modes, operating_metrics
interviewer_followups, reference_answer, rubric, repair_tasks
sources, related_algorithms
```

`reference_answer` 必须按面试交付顺序组织：框定问题、容量与关键假设、API/数据、主线架构、deep dive、取舍与风险。`rubric` 以工程判断评分，而非是否画出了指定组件。

## 产品边界

| 入口 | 消费 Case 的方式 | 成功产物 |
| --- | --- | --- |
| `$card` | 解释一个机制或 Case 的决策链 | 可理解的视觉记忆材料 |
| `$senior-sde-interview-script` | 把 Case 转为 30/90 秒或完整设计口述 | 候选人可直接说出的答案 |
| `$system-design-study-coach` | 分配 Case、收取 artifact、按 rubric 诊断 | 下一步 repair task 与进度记录 |
| GitHub Pages | 浏览课程、讲义、QA、mock | 透明的学习与打印界面 |

白板只负责让因果关系更容易被看见；它不取代 requirements、估算、数据模型或答案质量。

## 信息架构

```text
cases/                 # 唯一课程与题库真源
  week-01/
    bitly-core.case.json
    bitly-mock.case.json
curriculum/            # 周次、日期、算法 block 与 Case 引用
templates/             # Pages、lecture、QA、live mock 模板
docs/                  # 由 manifest 生成的静态站点
skills/                # 三个入口消费同一 manifest 的逻辑
plugins/.../skills/    # 由打包命令同步的发布副本
scripts/               # build, package, validate
```

不再由 HTML 反向解析课程内容。`plan_lookup` 直接读取 curriculum manifest；HTML 仅是渲染输出。

## 数据流与状态

1. 课程 manifest 选择本周 Case、阅读源、算法 block 与交付物。
2. Coach 将 Case 转为当天 assignment，并记录用户提交的白板、口述、算法与自评。
3. Mock 使用同一 Case 的 follow-up 与 rubric，输出维度分数和证据。
4. Repair 根据最低维度生成一个小而可验证的再练任务；完成后回写 attempt history。
5. Pages 从同一 manifest 渲染周页、讲义、Q&A 和 mock 页面。

首期进度记录使用本地 JSON，按用户可导出的 attempt log 设计；不引入账号、云端数据库或虚假的持久化承诺。

## 发布与一致性

- `cases/` 与 `curriculum/` 是唯一真源；生成器和内容源进入本仓库。
- root skill、plugin skill、Pages 一律由同一个打包命令生成或同步。
- release QA 必须验证：18 周 / 126 日覆盖、每个 Case 的必填字段、内部链接、plugin copy 与 canonical copy 一致、插件内 `plan_lookup` 可执行。
- 删除已经失效的 14 周路径假设；发布失败不得依赖人工目测。

## 迁移顺序

1. 修复现有 release QA 和 plugin 中遗留的 14 周引用，恢复发布可信度。
2. 建立 manifest schema 与 Week 1 的 Bitly Case，作为端到端样板。
3. 用样板生成 Week 1 的 Pages 与 Coach assignment，验证产物等价或更清晰。
4. 将其余 17 周逐周迁移，并在每周迁移后执行 coverage/release QA。
5. 最后再精简重复 renderer 的发布方式；这不阻塞 Case Core。

## 验收标准

- 安装 plugin 后，`Week 1 Day 1` 和 `Week 18 Day 7` 均可查询并返回可访问 Pages URL。
- 任一 Case 都能生成讲义、候选人答案、mock follow-up、评分与 repair task，不手写重复事实。
- Pages、standalone skills、plugin copies 对同一 Case 使用相同标题、链接、rubric 与日期。
- release QA 在干净 checkout 上通过；旧 14 周文件名不再出现在运行时依赖中。
