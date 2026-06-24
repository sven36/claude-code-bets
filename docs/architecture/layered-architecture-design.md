# Claude Code 架构分层设计指南

## 概述

Claude Code 采用 **9 层分层架构**，从下往上依次是：底层基础设施 → 业务逻辑 → 交互层。这个设计直接来自 Anthropic 官方架构，反映了生产级 AI 应用的最佳实践。

```
┌─────────────────────────────────────────────────┐
│   Layer 1: CLI Entry Point (cli.tsx)             │  ← 快速路径分发
│   优先级处理：--version > --daemon > main        │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│   Layer 2: Command & Router (main.tsx)           │  ← 命令解析 + 分发
│   Commander.js + 快速路径优化                   │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│   Layer 3: UI & REPL (screens/REPL.tsx)          │  ← 用户交互界面
│   React Ink 组件 + 状态管理                      │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│   Layer 4: Core Loop (query.ts + QueryEngine.ts) │  ← 会话流程控制
│   消息处理 + 工具执行 + 上下文管理               │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│   Layer 5: Tool System (tools/ + Tool.ts)        │  ← 工具调度
│   工具注册 + 权限检查 + 执行编排                 │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│   Layer 6: API & Providers (services/api/)       │  ← API 抽象
│   多提供商适配：Anthropic/OpenAI/Gemini等      │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│   Layer 7: Services (services/)                  │  ← 业务服务
│   认证、日志、分析、缓存等横切关注点             │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│   Layer 8: State & Bootstrap (state/ + bootstrap/)│ ← 全局状态
│   AppState、权限、配置、会话管理                 │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│   Layer 9: Utils & Types (utils/ + types/)       │  ← 基础设施
│   工具函数、类型定义、常量                       │
└─────────────────────────────────────────────────┘
```

---

## 分层详解

### Layer 1: CLI Entry Point (`src/entrypoints/cli.tsx`)

**职责**: 快速路径分发，最小化启动时间

**关键特性**:
- **零模块加载快速路径** (`--version`)：直接打印版本，无其他导入
- **按优先级处理**：从高性能路径到完整CLI的优先级链
- **Feature gate 集成**：编译时死代码消除

```typescript
// 快速路径示例：--version 零开销
if (args[0] === '--version') {
  console.log(`${MACRO.VERSION} (Claude Code)`)
  return  // 无任何其他模块加载
}

// 中等成本路径：--daemon-worker
if (feature('DAEMON') && args[0] === '--daemon-worker') {
  const { runDaemonWorker } = await import('../daemon/workerRegistry.js')
  await runDaemonWorker(args[1])
  return
}

// 完整路径：main.tsx
const { main: cliMain } = await import('../main.jsx')
await cliMain()
```

**为什么这样设计**：
- ✅ **启动性能**: 常用命令秒级启动，减少冷启动延迟
- ✅ **模块独立**: 各路径完全解耦，减少全局状态污染
- ✅ **特性灵活**: Feature flag 让特定功能可选，支持轻量级部署

---

### Layer 2: Command & Router (`src/main.tsx`)

**职责**: 命令解析、路由、会话初始化

**核心组件**:
```
main.tsx (6970 行)
├── Commander.js 初始化
├── 子命令注册 (mcp, server, ssh, auth, etc.)
├── 全局选项处理 (--model, --bare, --bg)
├── 会话恢复逻辑
└── REPL vs Headless 分发
```

**关键设计**:
- **子命令即服务**: 每个子命令独立模块化
  ```typescript
  program
    .command('mcp')
    .description('Manage MCP servers')
    .action(async (options) => {
      // MCP 子命令处理
    })
  ```

- **全局选项提前应用**:
  ```typescript
  program
    .option('--model <name>', 'Override default model')
    .option('--bare', 'Bare mode: API-key-only, no OAuth')
    .option('--bg', 'Background session management')
  ```

- **会话恢复中心化**:
  ```typescript
  // 跨所有命令的一致性恢复逻辑
  const session = await restoreSession(sessionId)
  const messages = await session.loadMessages()
  ```

**为什么这样设计**：
- ✅ **一致的UX**: 所有子命令共享相同的启动、认证、会话逻辑
- ✅ **易于扩展**: 新子命令只需注册，无需修改框架
- ✅ **可测试性**: 每个命令可独立单元测试

---

### Layer 3: UI & REPL (`src/screens/REPL.tsx`)

**职责**: 用户交互、状态展示、事件处理

**架构**:
```
REPL.tsx
├── App (全局提供者)
│   ├── FpsMetricsProvider
│   ├── StatsProvider
│   ├── AppStateProvider
│   └── ThemeProvider (@anthropic/ink)
├── Messages 列表
├── Prompt Input
└── Side Panels (权限、工具、通知)
```

**数据流**:
```
用户输入
  ↓
onSubmit(input)
  ↓
isSlashCommand? → 立即执行 : 加入队列
  ↓
query() [异步生成器]
  ↓
消息流 → 状态更新 → React 重新渲染
  ↓
UI 显示最新消息
```

**为什么这样设计**：
- ✅ **响应式**: React 组件自动追踪状态变化
- ✅ **流式渲染**: 流式响应实时显示，无需等待完整消息
- ✅ **独立的UI框架**: Ink 完全隔离的渲染引擎，不依赖具体终端实现

---

### Layer 4: Core Loop (`src/query.ts` + `src/QueryEngine.ts`)

**职责**: 会话流程控制、多轮对话、错误恢复

**主循环流程**:
```
query(params) [异步生成器]
  ↓
while (true) {
  1. 发送消息到 API (queryModelWithStreaming)
  2. 处理 tool_use 工具调用
  3. 执行工具 (runTools)
  4. 生成下一轮消息
  5. 错误恢复 (compact/retry)
  6. 检查终止条件 (stop_reason)
}
```

**关键机制**:
- **异步生成器模式**:
  ```typescript
  export async function* query(params: QueryParams) {
    for await (const event of stream) {
      yield message  // 实时 yield 消息
    }
    return terminal  // 最终结果
  }
  ```

- **错误恢复链**:
  ```typescript
  if (isWithheld413) {  // 上下文溢出
    // 1. Context collapse 压缩
    // 2. Reactive compact 自适应压缩
    // 3. Truncation 截断
  }
  if (isWithheldMaxOutputTokens) {
    // 1. Escalating retry (8k → 64k)
    // 2. Multi-turn recovery
  }
  ```

- **上下文管理**:
  ```typescript
  // 自动压缩超长对话
  const compacted = await contextCollapse.tryCollapse(messages)
  
  // 微压缩 (prompt cache 友好)
  const microcompacted = await apiMicrocompact.compact()
  ```

**为什么这样设计**：
- ✅ **鲁棒性**: 完整的错误恢复链，自动降级
- ✅ **成本优化**: 上下文压缩、缓存、token 预算
- ✅ **模块独立**: 核心循环与UI完全解耦

---

### Layer 5: Tool System (`src/tools/` + `src/Tool.ts`)

**职责**: 工具定义、调度、权限控制

**架构**:
```
Tool.ts (接口定义)
  ↓
tools.ts (工具注册表)
  ↓
tools/ (55+ 工具实现)
├── FileEditTool/
├── BashTool/
├── AgentTool/
└── ...
```

**工具接口**:
```typescript
interface Tool {
  name: string
  description: string
  cache_control?: CacheControl
  input_schema: JSONSchema
  
  // 执行方法
  execute(input: any, context: ToolUseContext): AsyncGenerator
  
  // 可选钩子
  backfillObservableInput?(input: Record<string, unknown>): void
  getDeferralStrategy?(): 'immediate' | 'deferred'
}
```

**权限检查流程**:
```
工具执行请求
  ↓
canUseTool(toolName, input, mode)
  ↓
根据权限模式:
  - 'ask': 用户确认
  - 'bypass': 直接执行
  - 'default': 规则检查 (allowedTools/deniedTools)
  ↓
yield 执行结果
```

**为什么这样设计**：
- ✅ **灵活性**: 55+ 工具高度模块化，易于添加/移除
- ✅ **权限隔离**: 细粒度的权限检查，保护用户安全
- ✅ **异步友好**: 工具执行完全异步，支持并发

---

### Layer 6: API & Providers (`src/services/api/`)

**职责**: API 请求构建、多提供商支持、流适配

**架构**:
```
services/api/
├── claude.ts (Anthropic 原生)
├── openai/
│   ├── client.ts (OpenAI SDK)
│   ├── convertMessages.ts
│   ├── convertTools.ts
│   └── streamAdapter.ts
├── gemini/
│   ├── client.ts
│   └── streamAdapter.ts
├── bedrock/ (AWS)
├── vertex/ (Google Cloud)
└── grok/ (xAI)
```

**多提供商适配原理**:
```typescript
// 统一接口
export async function queryModelWithStreaming(options: Options) {
  const provider = getAPIProvider()
  
  if (provider === 'openai') {
    // OpenAI API → Anthropic 格式转换
    const messages = anthropicMessagesToOpenAI(params)
    const stream = await openaiClient.create(messages)
    return adaptOpenAIStreamToAnthropic(stream)
  }
  
  if (provider === 'gemini') {
    // Gemini API → Anthropic 格式转换
    const request = buildGeminiRequest(params)
    const stream = await geminiClient.stream(request)
    return adaptGeminiStreamToAnthropic(stream)
  }
  
  // Anthropic 原生
  return await anthropicClient.messages.stream(params)
}
```

**为什么这样设计**：
- ✅ **格式统一**: 下游代码无需知道具体提供商
- ✅ **成本灵活**: 可随时切换提供商，无代码改动
- ✅ **流适配**: 各提供商的流格式完全透明

---

### Layer 7: Services (`src/services/`)

**职责**: 横切关注点、业务服务

**主要服务**:
```
services/
├── api/              # API 抽象 (已覆盖)
├── analytics/        # 分析、事件日志
├── oauth/            # 认证管理
├── mcp/              # MCP 服务器管理
├── compact/          # 上下文压缩
├── tools/            # 工具执行编排
├── notifier.ts       # 通知系统
├── preventSleep.ts   # 系统级别管理
└── policyLimits/     # 策略限制
```

**关键服务示例**:

**认证服务**:
```typescript
// services/oauth/
getAuthTokenSource()     // 获取认证源
refreshOAuthToken()      // 刷新令牌
validateForceLoginOrg()  // 验证组织
```

**分析服务**:
```typescript
// services/analytics/
logEvent('tengu_query_complete', {
  model,
  tokens: usage.output_tokens,
  duration_ms,
})
```

**MCP 服务**:
```typescript
// services/mcp/
getMCPServers()
connectToServer(config)
callMCPTool(toolName, input)
```

**为什么这样设计**：
- ✅ **关注点分离**: 每个服务单一职责
- ✅ **可替换性**: 实现可轻易替换 (e.g., 不同的分析后端)
- ✅ **可测试性**: 服务可独立 mock

---

### Layer 8: State & Bootstrap (`src/state/` + `src/bootstrap/`)

**职责**: 全局状态管理、运行时初始化

**Bootstrap 流程**:
```
cli.tsx (entry)
  ↓
init.ts (一次性初始化)
  ├── enableConfigs()     # 读取配置文件
  ├── reverifyApiKey()    # 验证 API 密钥
  ├── initializeTelemetry() # 初始化分析
  └── showTrustDialog()   # 信任对话
  ↓
main.tsx (命令注册)
  ↓
REPL.tsx (UI 启动)
```

**全局状态**:
```typescript
// src/state/AppState.tsx
interface AppState {
  messages: Message[]
  tools: Tool[]
  toolPermissionContext: {
    mode: 'ask' | 'default' | 'bypass'
    allowedTools?: string[]
    deniedTools?: string[]
  }
  mcpConnections: Record<string, MCPConnection>
  // ...
}

// src/bootstrap/state.ts
// 模块级单例，存储会话全局数据
const sessionId = getSessionId()
const projectRoot = getProjectRoot()
const authTokens = getClaudeAIOAuthTokens()
```

**为什么这样设计**：
- ✅ **一致性**: 单一真实源 (single source of truth)
- ✅ **可预测性**: React context + Zustand store
- ✅ **持久化**: 配置、会话、权限自动保存

---

### Layer 9: Utils & Types (`src/utils/` + `src/types/`)

**职责**: 工具函数、类型定义、常量

**关键模块**:
```
utils/
├── api.ts              # API 工具函数
├── messages.ts         # 消息处理、规范化
├── tokens.ts           # Token 计算
├── format.ts           # 格式化
├── fileStateCache.ts   # 文件缓存
├── permissions/        # 权限检查
├── model/
│   ├── model.ts        # 模型能力查询
│   └── providers.ts    # 提供商选择
└── config.ts           # 配置管理

types/
├── global.d.ts         # 全局类型、define 声明
├── message.ts          # 消息类型
├── command.ts          # 命令类型
└── permissions.ts      # 权限类型
```

---

## 关键设计原则

### 1. **分离关注点 (Separation of Concerns)**

每一层只负责一件事：
```
Layer 1: 快速路径分发
Layer 2: 命令解析
Layer 3: 用户交互
Layer 4: 业务逻辑
Layer 5: 工具调度
Layer 6: API 抽象
Layer 7: 横切关注点
Layer 8: 状态管理
Layer 9: 基础设施
```

**好处**: 修改业务逻辑时，无需触及UI；切换API提供商时，无需修改核心循环。

### 2. **依赖流向单向性**

```
UI 层 (REPL.tsx)
  ↓ 调用
Core Loop (query.ts)
  ↓ 调用
Tools + API (Tool.ts + services/api/)
  ↓ 调用
Utils + State (utils/ + state/)
```

**关键规则**: 低层不知道高层，高层依赖低层。

### 3. **异步生成器模式**

```typescript
// 而不是回调地狱或Promise链
export async function* query(params) {
  // 实时 yield 结果
  for await (const message of messages) {
    yield message  // 立即流式返回，不等待完整响应
  }
}
```

**优势**: 
- 支持取消 (abort controller)
- 实时渲染流式消息
- 错误可立即处理

### 4. **Feature Flag 驱动设计**

```typescript
if (feature('TRANSCRIPT_CLASSIFIER')) {
  // 自动模式特定逻辑
}
if (feature('DAEMON')) {
  // 守护进程特定逻辑
}
```

**优势**: 
- 编译时死代码消除 (code splitting)
- 轻量级部署变体
- A/B 测试友好

### 5. **多提供商抽象**

```
统一的 Anthropic API 格式 (在内部使用)
  ↓
OpenAI 客户端 → 转换 → 统一格式
Gemini 客户端 → 转换 → 统一格式
Bedrock 客户端 → 转换 → 统一格式
  ↓
下游代码无需知道具体提供商
```

**优势**: 可随时添加新提供商，无需修改核心代码。

---

## 与传统架构的对比

### 传统三层架构
```
表现层 (UI)
业务逻辑层 (BLL)
数据访问层 (DAL)
```

**问题**: AI 应用中，API 不是简单的数据库，而是复杂的 LLM 调用。

### Claude Code 9 层架构
```
优势:
✓ 更细粒度的关注点分离
✓ AI 特定的优化 (流、缓存、上下文压缩)
✓ 多提供商支持 (OpenAI/Gemini/Bedrock)
✓ 复杂的权限管理
✓ Agent 协调能力
```

---

## 实际应用指南

### 添加新功能时的分层流程

**例: 添加新工具 (WebSearch)**

1. **Layer 5**: 定义工具
   ```typescript
   // src/tools/WebSearchTool/index.ts
   export const webSearchTool: Tool = {
     name: 'web_search',
     execute: async function*(input, context) {
       const results = await context.fetch(...)
       yield { type: 'text', text: JSON.stringify(results) }
     }
   }
   ```

2. **Layer 5**: 注册工具
   ```typescript
   // src/tools.ts
   tools.push(webSearchTool)
   ```

3. **Layer 6**: (如需) 扩展 API 参数
   ```typescript
   // src/services/api/claude.ts
   const tools = [...allTools, { name: 'web_search', ... }]
   ```

4. **Layer 3**: (可选) UI 反馈
   ```typescript
   // src/screens/REPL.tsx
   // 自动通过消息流显示 web_search 结果
   ```

**完全无需修改核心循环或UI框架！**

### 添加新 API 提供商

1. **Layer 6**: 创建适配层
   ```typescript
   // src/services/api/newprovider/
   export function getNewProviderClient() { ... }
   export async function* streamNewProvider(params) { ... }
   export function adaptNewProviderToAnthropic(response) { ... }
   ```

2. **Layer 6**: 注册提供商
   ```typescript
   // src/services/api/claude.ts
   if (provider === 'newprovider') {
     return await streamNewProvider(params)
   }
   ```

3. **完成！** UI 和核心逻辑无任何改动。

---

## 总结

Claude Code 的 9 层架构设计反映了生产级 AI 应用的复杂性：

| 层级 | 目的 | 核心特性 |
|-----|------|--------|
| 1-2 | 启动优化 | 快速路径、特性门控 |
| 3-4 | 交互流程 | 响应式UI、多轮对话 |
| 5-6 | 能力抽象 | 工具系统、多提供商 |
| 7-8 | 横切关注 | 权限、分析、状态 |
| 9 | 基础设施 | 工具函数、类型 |

**为什么这样设计**：
- **可维护性**: 清晰的分层，易于定位和修复bug
- **可扩展性**: 新功能通常只需修改一两层
- **可测试性**: 每层可独立单元测试
- **可替换性**: 核心算法不依赖具体实现细节
- **性能**: 针对性优化 (流、缓存、压缩、预加载)
- **可观测性**: 完整的日志、指标、追踪

这种分层设计是高效团队必须掌握的架构思想。
