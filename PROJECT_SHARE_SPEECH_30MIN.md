# Claude Code Best 源码项目分享：30 分钟演讲稿

> 配套文档：`PROJECT_SHARE.md`  
> 建议听众：有 TypeScript/CLI/AI Agent 基础的工程师  
> 分享目标：用 30 分钟建立对项目整体架构、核心链路和二次开发入口的共同认知。

## 时间分配

| 时间 | 主题 | 目标 |
| --- | --- | --- |
| 0:00 - 2:00 | 开场与项目定位 | 说明这个项目解决什么问题 |
| 2:00 - 5:00 | 顶层结构和技术栈 | 建立仓库地图 |
| 5:00 - 10:00 | 分层架构总览 | 建立主线：CLI -> REPL -> QueryEngine -> query -> tools/API |
| 10:00 - 17:00 | Agentic Loop 深入 | 解释 Claude Code 为什么不是普通聊天 CLI |
| 17:00 - 22:00 | 工具系统与权限边界 | 解释模型如何安全地“做事” |
| 22:00 - 25:00 | 上下文、记忆与压缩 | 解释长任务如何持续运行 |
| 25:00 - 28:00 | 扩展体系与二次开发入口 | 告诉大家从哪里改 |
| 28:00 - 30:00 | 总结与 Q&A 引导 | 收束核心观点 |

---

## 0:00 - 2:00 开场与项目定位

大家好，今天我们用 30 分钟快速导读一下当前这个 `claude-code-best` 项目的源码结构。

这个项目表面上看是一个 Claude Code CLI 的源码还原和增强版，但如果从架构角度看，它更像是一个完整的“终端 Agent 平台”。它不是简单地把用户输入发给模型，再把模型回答打印出来；它真正复杂的地方在于：模型可以读文件、改文件、执行命令、调用 MCP、创建子 Agent、管理任务、压缩上下文，并且所有这些动作都要被权限系统和 UI 状态管理起来。

所以今天我们不逐行讲代码，而是抓住一条主线：

```text
CLI 启动
  -> 终端 UI 或 headless 输入
  -> QueryEngine 会话编排
  -> query.ts Agentic Loop
  -> Tool 系统执行真实动作
  -> API Provider 与模型通信
```

如果大家听完之后只记住一句话，我希望是：

> 这个项目的核心架构是“React/Ink 终端前端 + QueryEngine 会话编排 + query.ts Agentic Loop + Tool/Permission/API 三大基础设施”。

接下来我们从仓库结构开始看。

---

## 2:00 - 5:00 顶层结构和技术栈

先看顶层目录。这个项目是一个 Bun + TypeScript 的单仓库。

主目录里最重要的是这几个：

```text
src/        主应用源码
packages/   workspace 子包
docs/       文档站和架构说明
tests/      集成测试和 mocks
scripts/    开发、构建、健康检查脚本
vendor/     原生二进制或 vendored 资源
```

其中 `src/` 是绝对核心，当前有两千多个 TypeScript/TSX 文件；`packages/` 里放的是一些工作区包，比如 `@anthropic/ink`、Computer Use、NAPI 包、Remote Control Server 等。

技术栈上有几个关键词：

第一，运行时是 Bun。`package.json` 中要求 Bun，并且构建脚本 `build.ts` 用的是 `Bun.build`。

第二，语言是 TypeScript 和 TSX。UI 部分大量使用 React 组件，但它不是浏览器 UI，而是通过 Ink 渲染到终端。

第三，CLI 路由使用 Commander.js。主入口 `src/main.tsx` 负责命令解析、配置初始化、运行模式分发。

第四，模型通信主要在 `src/services/api/`。这里既有 Claude/Anthropic 的主实现，也有 OpenAI、Gemini、Grok 等兼容适配。

第五，工具系统使用 Zod 和 JSON Schema 来约束模型传来的参数。这个点很重要，因为模型输出不可信，任何工具执行前都要先校验输入。

开发时常用命令也比较直观：

```bash
bun install
bun run dev
bun run build
bun test
bun run lint
```

构建产物输出到 `dist/`，bin 名称是 `ccb` 和 `claude-code-best`。

这部分我们先建立一个地图：以后看到问题，先判断它属于 CLI 启动、UI、Agent Loop、工具、API、权限、上下文，还是插件扩展。

---

## 5:00 - 10:00 分层架构总览

接下来讲分层架构。这个项目可以粗略分成 7 层。

第一层是 CLI Bootstrap，对应 `src/entrypoints/cli.tsx`。

它做的事情非常克制：先看是不是 `--version` 这种快速路径，如果是，就直接输出，不加载整个应用。然后再判断是不是 Chrome MCP、Computer Use MCP、daemon worker、bridge 等特殊模式。只有常规路径才动态 import `src/main.tsx`。

这是一种典型的 CLI 冷启动优化：短命令不应该为 React、MCP、插件、SDK 支付全部启动成本。

第二层是 Command Router 和 Init，对应 `src/main.tsx`。

这个文件很大，负责初始化配置、认证、feature flags、policy limits、遥测、MCP、插件、skills、tools、commands，然后决定进入 REPL 还是 headless 模式。

第三层是前端层，有两个入口：

- 交互式终端 UI：`src/screens/REPL.tsx`
- 非交互/headless：`src/cli/` 下的 print、structured IO 等

这说明核心能力和 UI 是分离的。REPL 只是一个前端，SDK/headless 是另一个前端。

第四层是会话编排层，对应 `src/QueryEngine.ts`。

它负责维护一整个会话的状态：消息、成本、文件历史、权限拒绝、transcript、abort controller、skill discovery 等。

第五层是 Agentic Loop，对应 `src/query.ts`。

这是最核心的循环：调用模型、接收 tool_use、执行工具、把 tool_result 写回消息、继续调用模型，直到任务结束。

第六层是工具系统，对应 `src/Tool.ts`、`src/tools.ts` 和 `src/tools/`。

工具系统把模型的意图变成真实操作，例如读文件、改文件、执行 Bash、搜索代码、调用 MCP、创建 Agent。

第七层是服务和基础设施，例如：

- `src/services/api/`：模型 Provider
- `src/services/mcp/`：MCP 连接
- `src/utils/permissions/`：权限规则
- `src/services/compact/`：上下文压缩
- `src/utils/plugins/`：插件系统
- `src/state/`：AppState

用一张逻辑图表示就是：

```text
cli.tsx
  -> main.tsx
  -> REPL.tsx / src/cli
  -> QueryEngine.ts
  -> query.ts
  -> tools.ts + tools/*
  -> services/api + services/mcp + utils/permissions
```

这条链路就是后面读源码和排查问题的主线。

---

## 10:00 - 17:00 Agentic Loop 深入

现在进入今天最重要的部分：`src/query.ts` 里的 Agentic Loop。

普通聊天机器人通常是这样的：

```text
用户输入 -> 请求模型 -> 模型回答 -> 结束
```

但 Claude Code 这种 coding agent 是这样的：

```text
用户输入
  -> 请求模型
  -> 模型说我要读文件
  -> 系统真的读文件
  -> 把文件内容作为 tool_result 给模型
  -> 模型继续判断要改文件
  -> 系统真的改文件
  -> 把 diff 或结果给模型
  -> 模型继续运行测试
  -> 系统真的运行命令
  -> 最后模型总结
```

这个“思考、行动、观察、再思考”的循环，就是 Agentic Loop。

在源码中，`query()` 是一个 `AsyncGenerator`。这意味着它可以边执行边 yield 消息，UI 不需要等所有事情结束才展示。

核心流程可以拆成 5 步。

第一步，上下文预处理。

在每次请求模型前，系统会处理当前消息列表，可能包括：工具结果预算截断、snip compact、microcompact、context collapse、auto compact。这些动作的目标是把上下文控制在模型窗口内，同时尽量保留有价值信息。

第二步，流式调用模型。

`query.ts` 通过 API 层发起 streaming 请求。模型返回的可能是普通文本，也可能是 `tool_use`。当发现 `tool_use` 时，系统会收集工具名、参数和 tool_use id。

第三步，执行工具。

工具执行不是简单串行。项目里有 `runTools` 和 `StreamingToolExecutor` 两套关键逻辑。

如果工具是并发安全的，比如多个只读搜索，可以并行执行。默认最大并发是 10，可以通过 `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` 调整。

如果工具不是并发安全的，比如写文件、执行可能改变状态的命令，就要串行执行，避免竞态。

第四步，把工具结果写回消息。

工具执行后会产生 `tool_result`，这些结果会变成新的用户消息，追加到消息流里。然后下一轮模型调用就能看到真实世界的观察结果。

第五步，判断继续还是终止。

如果模型没有再发出工具调用，就可以完成。如果发生 prompt too long、max output tokens、fallback、stop hook 等情况，系统可能进入恢复或重试路径。如果达到 max turns、被 abort、错误不可恢复，也会终止。

这个循环背后的关键价值是：模型不用一次性规划完所有步骤，而是可以根据每一步真实反馈动态调整策略。

举个例子：用户说“修一下测试失败”。模型一开始不知道失败原因，它可能先运行测试，拿到报错；再读对应文件；再修改；再运行测试验证。这就必须依赖 Agentic Loop，而不是一次性问答。

所以 `src/query.ts` 是整个项目最值得精读的文件。它连接了模型、工具、上下文、错误恢复和终止条件。

---

## 17:00 - 22:00 工具系统与权限边界

接下来讲工具系统。工具系统解决的问题是：模型说“我要做某件事”，本地系统如何判断它能不能做、怎么做、怎么展示结果。

核心文件有三个：

- `src/Tool.ts`
- `src/tools.ts`
- `src/tools/`

`Tool.ts` 定义了工具的基本形态。一个工具不仅有 `name`，还包括：

- 输入 schema
- 描述生成函数
- `call()` 执行函数
- 是否启用
- 是否只读
- 是否并发安全
- 是否破坏性操作
- 权限上下文
- 结果大小限制
- 进度类型

这说明工具不是简单函数，而是一个结构化能力对象。

`tools.ts` 是工具注册表。它会根据 feature flag、环境变量、用户类型、MCP、插件等因素，组装当前真正可用的工具列表。

具体工具都在 `src/tools/` 下，比如：

```text
BashTool              执行 shell 命令
PowerShellTool        Windows PowerShell 命令
FileReadTool          读文件
FileWriteTool         写文件
FileEditTool          编辑文件
GlobTool/GrepTool     搜索代码
AgentTool             子 Agent
MCPTool               MCP 工具调用
WebSearchTool         Web 搜索
LSPTool               语言服务能力
TodoWriteTool         任务清单
SkillTool             Skills 调用
```

但工具系统必须和权限系统一起看。因为模型发出工具调用，不代表就应该执行。

权限裁决大致是这样：

```text
模型请求 tool_use
  -> 输入 schema 校验
  -> 工具自身权限检查
  -> allow/ask/deny 规则匹配
  -> hook 介入
  -> UI 弹窗或 headless callback
  -> 允许后才真正执行 call()
```

比如文件工具会检查路径是否在允许范围内；Bash 工具会分析命令是不是只读、是不是危险；Plan Mode 下写操作会被限制；Hook 可以进一步拦截。

这里有一个很重要的架构思想：

> 模型只提出意图，权限系统决定边界，工具系统负责执行。

这就是 coding agent 能安全落地的关键。如果没有这层边界，模型每次执行命令或改文件都可能造成不可控风险。

工具执行还有一个性能设计：只读且并发安全的工具可以并行，非只读或有副作用的工具串行。这个设计在大代码库搜索时非常有用，可以明显降低等待时间。

---

## 22:00 - 25:00 上下文、记忆与压缩

接下来讲上下文管理。

Agent 项目和普通应用最大的不同之一，是上下文窗口会成为核心资源。任务越长，消息越多，工具结果越大，越容易超过模型上下文限制。

这个项目围绕上下文做了很多工程化处理。

第一类是 System Prompt 和用户上下文组装。

相关逻辑在 `src/utils/queryContext.ts`、`src/constants/`、`src/context.ts` 等位置。它会把项目环境、工具说明、MCP 状态、日期、工作目录、记忆等信息组装给模型。

第二类是记忆。

包括 `CLAUDE.md`、项目记忆、session memory、nested memory。相关目录有 `src/memdir/`、`src/services/SessionMemory/`。`QueryEngine` 里也有 `loadedNestedMemoryPaths` 去重，避免同一份记忆被反复注入。

第三类是 token 计算和预算。

`src/utils/tokens.ts` 和 `src/utils/tokenBudget.ts` 会估算上下文长度、输出预算和是否需要压缩。

第四类是压缩。

主要包括：

- `autoCompact`：正常运行中超过阈值自动压缩
- `reactiveCompact`：遇到 prompt too long 后恢复性压缩
- `contextCollapse`：折叠上下文片段
- `microcompact`：对局部信息做轻量压缩

第五类是工具结果落盘。

如果工具结果太长，`toolResultStorage` 可以把完整结果保存到文件，只把预览和路径给模型。这样既不丢信息，也避免把上下文撑爆。

这部分可以总结成一句话：

> Claude Code 把上下文窗口当成一等资源来管理，而不是简单地把所有历史消息塞给模型。

这也是它能处理长任务、多工具调用和大型项目的基础。

---

## 25:00 - 28:00 扩展体系与二次开发入口

最后看扩展体系。这个项目的扩展点很多，主要有四类。

第一类是 Slash Commands。

如果要新增 `/xxx` 命令，主要看：

```text
src/commands/
src/commands.ts
src/types/command.ts
```

命令可以是本地 UI 命令，也可以是 prompt 命令，还可以支持 headless 模式。

第二类是 Tools。

如果要新增模型可调用工具，主要看：

```text
src/Tool.ts
src/tools.ts
src/tools/*
```

推荐先参考 `FileReadTool`、`FileEditTool` 或 `BashTool`，因为这些工具覆盖了 schema、权限、UI 展示和结果处理的典型模式。

第三类是 API Provider。

如果要接入新的模型协议，看：

```text
src/services/api/
src/services/api/openai/
src/services/api/gemini/
src/services/api/grok/
```

通常需要处理消息转换、工具转换、stream adapter 和 model mapping。

第四类是 MCP、Plugins、Skills。

MCP 相关看 `src/services/mcp/` 和 `src/tools/MCPTool/`。

插件相关看 `src/utils/plugins/`、`src/services/plugins/`。

Skills 相关看 `src/skills/`、`src/tools/SkillTool/`、`src/services/skillSearch/`。

如果是改 UI，看 `src/screens/REPL.tsx`、`src/components/`、`src/hooks/` 和 `packages/@ant/ink/`。

如果是改权限，看 `src/utils/permissions/`、`src/hooks/useCanUseTool.ts` 和各工具的权限检查逻辑。

如果是改上下文压缩，看 `src/services/compact/`、`src/services/contextCollapse/` 和 `src/utils/tokens.ts`。

所以二次开发前，先判断自己是在扩展“命令”“工具”“模型 Provider”“UI”“权限”还是“上下文”。不要直接从 `main.tsx` 或 `REPL.tsx` 开始硬啃。

---

## 28:00 - 30:00 总结与 Q&A 引导

最后我们做一个收束。

这个项目的复杂度来自三件事叠加。

第一，它是一个复杂 CLI。要考虑启动性能、跨平台、终端渲染、快捷键、headless 输出。

第二，它是一个复杂 Agent。要考虑多轮循环、工具调用、上下文压缩、错误恢复、成本追踪。

第三，它是一个平台。要支持 MCP、插件、Skills、子 Agent、远程控制、多 Provider 和 feature flags。

今天最重要的主线是：

```text
src/entrypoints/cli.tsx
  -> src/main.tsx
  -> src/screens/REPL.tsx 或 src/cli/
  -> src/QueryEngine.ts
  -> src/query.ts
  -> src/Tool.ts + src/tools.ts + src/tools/
  -> src/services/api/ + src/services/mcp/ + src/utils/permissions/
```

如果后面大家要继续读源码，我建议分三次读：

第一次，只读主链路，跑通从用户输入到工具执行的路径。

第二次，选一个工具深入，比如 `FileEditTool` 或 `BashTool`，看它怎么做 schema、权限和结果展示。

第三次，再读上下文压缩和 Provider 适配，这两块是高级能力，也是长任务稳定性的关键。

最后再重复一句核心总结：

> Claude Code Best 不是一个聊天壳子，而是一套终端 Agent 运行时。它用 QueryEngine 管会话，用 query.ts 跑 Agentic Loop，用 Tool 系统连接真实世界，用 Permission 系统守住边界。

我的分享就到这里，接下来可以讨论几个问题：

1. 如果我们要新增一个内部工具，应该走 Tool 还是 MCP？
2. 如果要接入新的模型服务，Provider 适配最小改动点在哪里？
3. 当前权限模型是否满足我们的使用场景？
4. 对长任务来说，压缩策略和 transcript 是否还需要增强？

---

## 备用：现场演示建议

如果分享时允许现场演示，可以用 3 分钟补充：

```bash
bun run dev
```

演示重点不要放在功能炫技，而是放在源码映射：

1. 启动命令对应 `src/entrypoints/cli.tsx` 和 `src/main.tsx`。
2. 输入框和消息列表对应 `src/screens/REPL.tsx`。
3. 一次模型请求对应 `src/QueryEngine.ts` 和 `src/query.ts`。
4. 文件读取/搜索/命令执行对应 `src/tools/`。
5. 权限弹窗对应 `canUseTool` 和 `ToolPermissionContext`。

这样听众会更容易把运行时现象和源码结构对应起来。
