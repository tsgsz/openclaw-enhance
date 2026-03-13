# openclaw-enhance

本项目用于对 Openclaw 做智力和稳定性上的增强。

> **For OpenCode sessions**: Start with [`AGENTS.md`](./AGENTS.md) for project rules and [`docs/opencode-iteration-handbook.md`](./docs/opencode-iteration-handbook.md) for current design state.

1. 不侵入 Openclaw 的源代码，一切能力都用 plugin, hooks, skills, agents定义来实现。
2. 不修改任何运行时的的文件：例如 main 的 AGENTS.md, TOOLS.md 等。
3. 可以一键部署或者卸载。
4. 尽可能不直接修改配置，优先使用openclaw的cli 命令来进行操作。
5. 尽可能不侵入式改变 openclaw 的工作逻辑，只是提供了工具。

## 要解决的问题

1. 原生 Openclaw 在同时进行多任务时，智力显著下降。
2. 原生 Openclaw 在遇到大段的TOOLS调用时，无法响应用户的其它要求。
3. 原生 Openclaw 的 main 在 sessions_spawn 之后，subagent 会直接返回结果。
4. 原生 Oepnclaw 的 main 在干活的时候不会给大概要干多就的预期，有时候 subagent 挂了也不会多说话。
5. 原生 Openclaw 的文件写入全靠大模型临时编，受记忆影响非常大，后期无法管理。

## 多任务方案

1. 创建一个 和 main 一样强的 Agent，同样都用最好的模型: Orchestrator, 该 Agent 会所有的技能，并且每次都会使用 planning-with-files 以及 superpowers 来进行任务规划。
2. 为 main 创建一个 skill，当 main 进行任务分发的时候，可以预估大概要多久的时间。
3. 为 main 创建一个 skill, 当 main 将要执行的任务被认为 TOOLCALL 大于 2的时候，main 会分发给 orchestrator.
4. 为 Orchestrator 创建一组 Agent，来帮助他解决更加具体的子任务。
5. 为 Orchestrator 创建一个 skill，他可以查看当前所有的项目，以及创建新的项目，并决定是什么类型的项目，以及工作目录放在哪里。
6. 为 Orchestrator 创建一个 skill，对于特定的任务，他可以分发给特定的 subagent 去干。
7. 为 Orchestrator 创建一个 skill，用于在编码任务里面完成 agentos 的实践。
8. 为 Orchestrator 创建一个 skill，用于进行项目级别的 git hisstory 的额外信息注入。
9. 为 Orchestrator 和 main 都创建一个 skill， 当接收到 task 超时时修改 runtime 状态。

## 多 Agent 方案

功能类 Agent 和 TOOLS 类似，是为了执行某个具体的任务，只不过中间需要有 LLM 做模糊判断。功能类的 AGENT 理论上可以由 Orchestrator + skills 来取代， 但是这里单独抽象出来时因为可以固定死开放的工具和skill，来进行更好的分工。

1. searcher：用于搜索，调研，便宜模型+沙盒读写。
2. syshelper: 用于系统搜索：grep，session_list, ls 便宜模型+只读。
3. script_coder: 用于脚本编写测试：codex类模型+沙盒读写。
4. watchdog：用于 openclaw 系统诊断：包括判断某个session是否结束，是否超时，便宜模型+读写。watchdog有session_send的权限。
     a. 为watchdog创建一个skill，当发现session超时的情况时send到原session进行提醒。
     b. 为watchdog创建一个skill，学会如何判断session的状态。
5. acp：opencode 用于开发，无需新建专门的Agents，但是要在 Orchestrator 的分发skill体现出来。

## hooks

1. 监听subagent_spawning, 当 spawn 之后写入额外task信息，包括所属 project，以及 ETA。

## scripts

1. 创建一个脚本监控 runtime, 发现有超时则告诉 watchdog，由他来做实际的判断。并且例行此脚本，1分钟检测一次