# 12 周系统设计路线重构设计

## 已确认目标

本次重构以用户已确认的 Week 1 节奏为基准：每个 Hello Interview
Question Breakdown 都必须先有一个从 `Understanding the Problem` 连续读到
`High-Level Design` 的完整通读日，再有一个覆盖 `Potential Deep Dives`、Senior
预期、真实追问和修复任务的深挖日。12 周覆盖官网当前 30 个 breakdown；项目按
内容复杂度分组，但不再分“主项目 / 迁移项目”，也不允许用压缩题替代完整学习。

## 唯一真源

仓库内保留四类可审计输入：

1. `sources/source-manifest.json`：外链页面的原站显示标题、canonical URL、
   真实 HTML heading id，以及最后一次验证结果所对应的内容摘要。
2. `cases/*.json`：30 个项目的学习判断、讲义骨架、Senior/Staff 追问、参考答案、
   repair task 与精确来源引用。
3. `curriculum/route.json`：12 周、84 天的项目日历、每日时间段、项目阶段和
   NeetCode block。
4. `curriculum/algorithm-blocks.json`：每天恰好 3 道题，按 NeetCode tag 连续推进，
   不与系统设计主题强行绑定。
5. `curriculum/audio-preview.json`：试听策略与默认参数。每周只提供约 2 分钟的中文
   讲译脚本和用户主动选择的生成入口；默认使用
   `Siqi Liu - Calm, Warm and Gentle` 与 `Eleven v3`，构建和页面均不得调用
   ElevenLabs API、批量生成或消耗 credits。

`docs/`、每周 curriculum JSON 和 plugin 内副本都是生成物，不再反向解析 HTML。

## 重构前审计结论

审计覆盖 AgentCoach 中既有课程生成路径和独立发布仓库。旧发布物仍保留 18 周、
Week 1 特殊文件名和多套相互漂移的 HTML / curriculum / plugin 副本；旧链路没有
把“官网 30 题目录、精确标题、真实 fragment、case 引用、运行时 manifest”绑定成
同一份可失败的合同。部分周的讲义和问答还复用了跨项目句式，链接即使可打开也不能
证明与问题语义匹配。旧生成器会先删除整周目录再渲染，晚期失败可能留下半套站点；
plugin 同步也采用 delete-before-copy。

因此本次不在有用户未提交内容的 AgentCoach 工作树内就地改写，而在独立发布仓库
建立 manifest → case → route → staged output 的单向链路。构建先在临时目录完成，
发布时只替换生成器拥有的明确文件并保留回滚副本；plugin 也先完整 staging，再做
可回滚目录交换。旧 Week 13–18 只按已知生成文件清理，不删除未知同目录文件。

## 生成与验证顺序

标准构建链路为：

```text
live source verification
  -> manifest / case / route structural validation
  -> static page generation
  -> plugin sync
  -> release QA
```

外链验证器抓取每个被引用页面，检查 HTTP 成功、页面显示标题和每个 fragment 的
真实 heading id；Hello Interview 的 30 题清单还必须与官方目录逐项一致。任何
页面、标题或 anchor 无法验证时构建立刻失败，不降级为页面级泛链，也不生成猜测
alias。离线 QA 可以读取同一 manifest，但正式生成必须先产生与 manifest digest
匹配的 live verification report。

## 12 周路由

| 周 | 项目 |
|---|---|
| 1 | Bitly、Dropbox |
| 2 | Rate Limiter、Distributed Cache、Job Scheduler |
| 3 | WhatsApp、FB Live Comments、Online Chess |
| 4 | FB News Feed、Instagram、YouTube |
| 5 | Google Docs、LeetCode |
| 6 | Ticketmaster、Online Auction、Payment System |
| 7 | Robinhood、Uber |
| 8 | Tinder、Local Delivery Service、Yelp |
| 9 | News Aggregator、FB Post Search、Web Crawler |
| 10 | Metrics Monitoring、Ad Click Aggregator、YouTube Top K |
| 11 | Price Tracking Service、Strava |
| 12 | ChatGPT 与全路线 capstone |

三项目周使用六个项目日加一个 mock/repair 日。两项目周使用四个项目日，剩余三天
做关联概念、双题 mock 和 repair。ChatGPT 周用两天完成项目，再以其余五天完成
GPU 调度、流式输出、长上下文成本、官方 OpenAI/Anthropic 延伸和 30 题综合复测。
官方 AI 文档只能出现在这一周。

## 页面合同

每周生成：

- 周概览：项目日历、每日精确时间段和直达入口。
- 7 个每日页：精确小节链接、任务、产出、验收标准、失败后的修复路径和 3 道算法。
- 中文深度讲义：逐项目解释状态、主路径、正确性边界、扩展触发器、失败语义和指标，
  不能只是组件清单。
- Staff Q&A：逐项目的真实追问、触发条件、详细答案、常见误区、追问和来源。
- GPT Live mock：一次只问一个问题，按候选人回答动态深挖，结束后以证据评分并指定
  repair。
- scorecard / 复盘页：记录设计证据、critical miss、修复动作和复测结果。
- 音频预听：显示本周约 2 分钟中文讲译脚本、复制按钮、已确认的 Voice/Model，
  并清楚标记“不会自动生成”；可选入口同样必须通过精确标题与真实 anchor 验证。

Week 1 必须同时覆盖 API、data modeling、caching、indexing、networking、
large blobs、CDN、DynamoDB/Postgres、realtime、CAP 与相应 DDIA 小节，并删除
与 Bitly/Dropbox 无关的 Applied AI overlay。

## QA 闸门

发布前必须验证：

- 官方目录恰好 30 题，全部且只出现一次；每题有完整通读日和深挖日。
- 恰好 12 周、84 天、252 个 required algorithm slots；每天恰好 3 题。
- 所有日页有可执行时间段、产出、验收和 repair；所有周有 lecture、Q&A、mock、
  scorecard。
- 所有外链、标题和 fragment live 验证通过；所有内部链接目标存在。
- 讲义和 Q&A 通过最低深度、来源、项目特异性与禁用泛化问句检查，并人工抽样。
- AI 官方扩展只存在于 ChatGPT 项目。
- 12 周均有达到时长目标的中文试听脚本；默认 Voice/Model 固定，且
  `auto_generate=false`。
- 生成输出与 plugin 副本一致，release QA 在干净工作树可复现。

## 发布

在独立、干净的发布仓库 `main` 上提交本次变更，不触碰 AgentCoach 当前工作树中
与课程无关的未提交文件。推送后轮询 GitHub Pages，确认首页、总路线、Week 1、
Week 12 以及抽样锚点返回新提交内容。
