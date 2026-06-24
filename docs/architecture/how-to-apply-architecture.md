# 在你的 Agent/CLI 项目中应用分层架构

## 快速开始

本指南教你如何在自己的项目中应用 Claude Code 的分层设计。

---

## 第一步: 规划你的分层

### 对于小项目 (< 5000 行)

```
Layer 1: Entry Point
  ├── 快速路径 (--version, --help)
  └── 完整路径 (主程序)

Layer 2: Router
  ├── 子命令注册
  └── 参数解析

Layer 3: Core Logic
  ├── 主循环 (async generator 或 Promise)
  └── 工具编排

Layer 4: Services
  ├── API 调用
  ├── 数据处理
  └── 权限检查

Layer 5: Utils
  ├── 工具函数
  ├── 类型定义
  └── 常量
```

### 对于大项目 (> 10000 行)

直接参考 Claude Code 的 9 层架构。

---

## 第二步: 实现 Entry Point (Layer 1)

### 示例: 你的 CLI 启动

```typescript
// src/entrypoints/cli.ts
import path from 'path'

export async function main() {
  const args = process.argv.slice(2)
  
  // 快速路径 1: 版本信息
  if (['--version', '-v'].includes(args[0])) {
    console.log('1.0.0')
    return
  }
  
  // 快速路径 2: 帮助信息
  if (['--help', '-h'].includes(args[0]) && !args[1]) {
    console.log('Usage: mycli [command] [options]')
    return
  }
  
  // 完整路径: 加载主程序
  const { runCli } = await import('../cli/index.js')
  await runCli(args)
}

if (require.main === module) {
  main().catch(console.error)
}
```

### bin/mycli 脚本

```bash
#!/usr/bin/env node
require('../dist/entrypoints/cli.js').main()
```

### 性能收益

```
快速路径 (--version):    50ms (无任何模块加载)
完整路径 (normal):       500ms (加载所有代码)
```

---

## 第三步: 实现 Router (Layer 2)

### 使用 Commander.js (推荐)

```typescript
// src/cli/index.ts
import { Command } from 'commander'
import { version } from '../../package.json'

export async function runCli(args: string[]) {
  const program = new Command()
  
  program
    .version(version)
    .description('My awesome CLI')
  
  // 全局选项
  program
    .option('--model <name>', 'Override model')
    .option('--api-key <key>', 'Anthropic API key')
    .option('--debug', 'Enable debug logging')
  
  // 子命令 1: chat
  program
    .command('chat')
    .description('Start interactive chat')
    .action(async (options) => {
      const { runChat } = await import('../commands/chat.js')
      await runChat(options)
    })
  
  // 子命令 2: ask
  program
    .command('ask <question>')
    .description('Ask a single question')
    .action(async (question, options) => {
      const { runAsk } = await import('../commands/ask.js')
      await runAsk(question, options)
    })
  
  // 子命令 3: agent
  program
    .command('agent')
    .description('Run autonomous agent')
    .option('--max-steps <n>', 'Max iterations', '10')
    .action(async (options) => {
      const { runAgent } = await import('../commands/agent.js')
      await runAgent(options)
    })
  
  await program.parseAsync(args)
}
```

**关键特性**:
- ✅ 子命令完全解耦
- ✅ 参数自动验证
- ✅ 帮助信息自动生成
- ✅ 易于测试

---

## 第四步: 实现 Core Loop (Layer 3)

### 案例: 聊天循环

```typescript
// src/core/chatLoop.ts
import { Message } from '../types'

interface ChatLoopParams {
  initialPrompt: string
  model: string
  apiKey: string
  systemPrompt?: string
}

export async function* chatLoop(params: ChatLoopParams) {
  const { initialPrompt, model, apiKey, systemPrompt } = params
  
  const messages: Message[] = [
    { role: 'user', content: initialPrompt },
  ]
  
  const system = systemPrompt || 'You are a helpful assistant.'
  
  // 多轮对话循环
  while (true) {
    // Step 1: 发送消息到 API
    yield { type: 'status', message: 'Thinking...' }
    
    const response = await queryModel(
      { messages, system, model, apiKey }
    )
    
    // Step 2: 处理响应
    const assistantMessage = response.content
    messages.push({
      role: 'assistant',
      content: assistantMessage,
    })
    
    yield {
      type: 'message',
      role: 'assistant',
      content: assistantMessage,
    }
    
    // Step 3: 检查停止条件
    if (response.stop_reason === 'end_turn') {
      break
    }
    
    if (response.stop_reason === 'tool_use') {
      // 处理工具调用 (Step 4)
      const tools = response.content.filter(b => b.type === 'tool_use')
      for (const toolCall of tools) {
        yield {
          type: 'tool_use',
          toolName: toolCall.name,
          toolInput: toolCall.input,
        }
        
        // 执行工具
        const toolResult = await executeTool(
          toolCall.name,
          toolCall.input
        )
        
        messages.push({
          role: 'user',
          content: [
            {
              type: 'tool_result',
              tool_use_id: toolCall.id,
              content: JSON.stringify(toolResult),
            },
          ],
        })
        
        yield {
          type: 'tool_result',
          toolName: toolCall.name,
          result: toolResult,
        }
      }
      
      // 继续循环处理工具结果
      continue
    }
    
    // Step 5: 其他停止原因
    break
  }
}

// 类型定义
type ChatLoopEvent =
  | { type: 'status'; message: string }
  | { type: 'message'; role: 'user' | 'assistant'; content: string }
  | { type: 'tool_use'; toolName: string; toolInput: unknown }
  | { type: 'tool_result'; toolName: string; result: unknown }
```

### 在 UI 中使用

```typescript
// src/commands/chat.ts
import { createInterface } from 'readline'
import { chatLoop } from '../core/chatLoop'

export async function runChat(options: any) {
  const readline = createInterface({
    input: process.stdin,
    output: process.stdout,
  })
  
  const prompt = (question: string): Promise<string> => {
    return new Promise(resolve => {
      readline.question(question, resolve)
    })
  }
  
  const initialPrompt = await prompt('You: ')
  
  // 开始对话循环
  for await (const event of chatLoop({
    initialPrompt,
    model: options.model || 'claude-3-5-sonnet',
    apiKey: options.apiKey || process.env.ANTHROPIC_API_KEY,
  })) {
    if (event.type === 'status') {
      console.log(`\n[${event.message}]`)
    } else if (event.type === 'message') {
      console.log(`\nAssistant: ${event.content}`)
    } else if (event.type === 'tool_use') {
      console.log(`\n[Using tool: ${event.toolName}]`)
    } else if (event.type === 'tool_result') {
      console.log(`[Tool result: ${JSON.stringify(event.result)}]`)
    }
  }
  
  readline.close()
}
```

**关键优势**:
- ✅ 复杂的循环逻辑完全独立
- ✅ 可被不同的 UI 调用
- ✅ 易于测试和调试
- ✅ 支持流式处理

---

## 第五步: 实现 Tool System (Layer 4)

### 定义工具接口

```typescript
// src/types/tool.ts
export interface Tool {
  name: string
  description: string
  input_schema: {
    type: 'object'
    properties: Record<string, any>
    required?: string[]
  }
  execute(input: unknown): Promise<unknown>
}
```

### 实现工具

```typescript
// src/tools/MathTool.ts
import { Tool } from '../types'

export const mathTool: Tool = {
  name: 'calculator',
  description: 'Performs mathematical operations',
  input_schema: {
    type: 'object',
    properties: {
      expression: {
        type: 'string',
        description: 'Math expression (e.g., "2+2*3")',
      },
    },
    required: ['expression'],
  },
  async execute(input: unknown) {
    const { expression } = input as { expression: string }
    
    // 简单示例: 实际项目应使用 math.js 或 expr-eval
    const result = eval(expression)
    
    return { result, expression }
  },
}

// src/tools/WebFetchTool.ts
export const webFetchTool: Tool = {
  name: 'fetch_url',
  description: 'Fetch content from a URL',
  input_schema: {
    type: 'object',
    properties: {
      url: {
        type: 'string',
        description: 'URL to fetch',
      },
    },
    required: ['url'],
  },
  async execute(input: unknown) {
    const { url } = input as { url: string }
    
    const response = await fetch(url)
    const text = await response.text()
    
    return { 
      url,
      status: response.status,
      content: text.slice(0, 1000), // 限制大小
    }
  },
}
```

### 工具注册

```typescript
// src/tools/index.ts
import { mathTool } from './MathTool'
import { webFetchTool } from './WebFetchTool'

export const allTools = [
  mathTool,
  webFetchTool,
  // 添加更多工具...
]

export function getTool(name: string) {
  return allTools.find(t => t.name === name)
}
```

### 在核心循环中使用

```typescript
// 在 chatLoop.ts 中
async function executeTool(name: string, input: unknown) {
  const tool = getTool(name)
  
  if (!tool) {
    throw new Error(`Tool not found: ${name}`)
  }
  
  return await tool.execute(input)
}
```

---

## 第六步: 实现多 API 提供商支持 (Layer 5)

### API 抽象接口

```typescript
// src/services/api.ts
export interface APIProvider {
  queryModel(params: QueryParams): Promise<QueryResponse>
  streamModel(params: QueryParams): AsyncIterable<StreamEvent>
}

export interface QueryParams {
  messages: Message[]
  system?: string
  model: string
  tools?: Tool[]
}

export interface QueryResponse {
  content: ContentBlock[]
  stop_reason: string
  usage: { input_tokens: number; output_tokens: number }
}

export type StreamEvent =
  | { type: 'message_start'; message: any }
  | { type: 'content_block_start'; index: number; content_block: any }
  | { type: 'content_block_delta'; delta: any }
  | { type: 'message_delta'; delta: any }
  | { type: 'message_stop' }
```

### Anthropic 实现

```typescript
// src/services/api/anthropic.ts
import Anthropic from '@anthropic-ai/sdk'
import { APIProvider, QueryParams, StreamEvent } from '../api'

export class AnthropicProvider implements APIProvider {
  private client: Anthropic
  
  constructor(apiKey: string) {
    this.client = new Anthropic({ apiKey })
  }
  
  async queryModel(params: QueryParams) {
    const response = await this.client.messages.create({
      model: params.model,
      max_tokens: 4096,
      system: params.system,
      messages: params.messages,
      tools: params.tools?.map(tool => ({
        name: tool.name,
        description: tool.description,
        input_schema: tool.input_schema,
      })),
    })
    
    return {
      content: response.content,
      stop_reason: response.stop_reason,
      usage: response.usage,
    }
  }
  
  async *streamModel(params: QueryParams): AsyncIterable<StreamEvent> {
    const stream = await this.client.messages.stream({
      model: params.model,
      max_tokens: 4096,
      system: params.system,
      messages: params.messages,
      tools: params.tools?.map(tool => ({
        name: tool.name,
        description: tool.description,
        input_schema: tool.input_schema,
      })),
    })
    
    for await (const event of stream) {
      yield event
    }
  }
}
```

### OpenAI 兼容实现

```typescript
// src/services/api/openai.ts
import OpenAI from 'openai'
import { APIProvider, QueryParams, StreamEvent } from '../api'

export class OpenAIProvider implements APIProvider {
  private client: OpenAI
  
  constructor(apiKey: string, baseUrl?: string) {
    this.client = new OpenAI({
      apiKey,
      baseURL: baseUrl,
    })
  }
  
  async queryModel(params: QueryParams) {
    const response = await this.client.chat.completions.create({
      model: params.model,
      messages: params.messages.map(m => ({
        role: m.role,
        content: m.content,
      })),
      tools: params.tools?.map(tool => ({
        type: 'function',
        function: {
          name: tool.name,
          description: tool.description,
          parameters: tool.input_schema,
        },
      })),
    })
    
    // 转换为统一格式
    return {
      content: this.convertOpenAIContent(response.choices[0].message),
      stop_reason: response.choices[0].finish_reason,
      usage: {
        input_tokens: response.usage?.prompt_tokens || 0,
        output_tokens: response.usage?.completion_tokens || 0,
      },
    }
  }
  
  private convertOpenAIContent(message: any) {
    // 实现 OpenAI 格式到 Anthropic 格式的转换
    const content = []
    
    if (message.content) {
      content.push({ type: 'text', text: message.content })
    }
    
    if (message.tool_calls) {
      for (const toolCall of message.tool_calls) {
        content.push({
          type: 'tool_use',
          id: toolCall.id,
          name: toolCall.function.name,
          input: JSON.parse(toolCall.function.arguments),
        })
      }
    }
    
    return content
  }
  
  async *streamModel(params: QueryParams): AsyncIterable<StreamEvent> {
    // 实现 OpenAI 流适配
    // ...
  }
}
```

### 提供商选择

```typescript
// src/services/provider.ts
import { AnthropicProvider } from './api/anthropic'
import { OpenAIProvider } from './api/openai'

export function getAPIProvider(
  modelType: string = 'anthropic',
  config: any = {}
): APIProvider {
  const apiKey = process.env.ANTHROPIC_API_KEY
  
  if (!apiKey && modelType === 'anthropic') {
    throw new Error('ANTHROPIC_API_KEY not set')
  }
  
  switch (modelType) {
    case 'openai':
      return new OpenAIProvider(
        process.env.OPENAI_API_KEY || apiKey,
        process.env.OPENAI_BASE_URL
      )
    
    case 'anthropic':
    default:
      return new AnthropicProvider(apiKey)
  }
}
```

**结果**: 现在可以轻松切换 API 提供商而无需改动核心逻辑！

---

## 第七步: 集成测试

### 测试工具系统

```typescript
// tests/tools.test.ts
import { describe, it, expect } from 'bun:test'
import { mathTool } from '../src/tools/MathTool'

describe('MathTool', () => {
  it('should calculate expressions', async () => {
    const result = await mathTool.execute({ expression: '2+2' })
    expect(result.result).toBe(4)
  })
})
```

### 测试核心循环

```typescript
// tests/chatLoop.test.ts
import { chatLoop } from '../src/core/chatLoop'

it('should handle single turn conversation', async () => {
  const events = []
  
  for await (const event of chatLoop({
    initialPrompt: 'Hello',
    model: 'claude-3-5-sonnet',
    apiKey: 'test-key',
  })) {
    events.push(event)
  }
  
  // 验证事件序列
  expect(events).toContainEqual(
    expect.objectMatching({ type: 'message', role: 'assistant' })
  )
})
```

---

## 完整项目结构

```
my-agent/
├── src/
│   ├── entrypoints/
│   │   └── cli.ts          # Layer 1: 快速路径
│   ├── cli/
│   │   └── index.ts        # Layer 2: 命令路由
│   ├── commands/
│   │   ├── chat.ts         # Layer 2: 子命令
│   │   ├── ask.ts
│   │   └── agent.ts
│   ├── core/
│   │   ├── chatLoop.ts     # Layer 3: 核心循环
│   │   └── agentLoop.ts
│   ├── tools/              # Layer 4: 工具系统
│   │   ├── MathTool.ts
│   │   ├── WebFetchTool.ts
│   │   └── index.ts
│   ├── services/           # Layer 5: 服务层
│   │   ├── api.ts
│   │   ├── api/
│   │   │   ├── anthropic.ts
│   │   │   └── openai.ts
│   │   └── provider.ts
│   ├── types/              # Layer 6: 类型定义
│   │   ├── tool.ts
│   │   ├── message.ts
│   │   └── api.ts
│   └── utils/              # Layer 7: 工具函数
│       ├── format.ts
│       └── logger.ts
├── tests/
│   ├── tools.test.ts
│   ├── chatLoop.test.ts
│   └── api.test.ts
├── bin/
│   └── my-agent            # 可执行文件
├── package.json
└── tsconfig.json
```

---

## 清单

在开始之前，确认你已完成：

- [ ] 规划好你的分层 (通常 5-7 层即可)
- [ ] 实现 Entry Point (快速路径 + 完整路径)
- [ ] 选择命令框架 (推荐 Commander.js)
- [ ] 实现核心循环 (异步生成器)
- [ ] 定义工具接口和实现
- [ ] 抽象 API 提供商
- [ ] 编写单元测试
- [ ] 编写集成测试
- [ ] 文档化架构决策

---

## 总结

遵循这个指南，你可以构建：
- ✅ 启动快速的 CLI
- ✅ 易于扩展的工具系统
- ✅ 可测试的核心逻辑
- ✅ 灵活的 API 支持
- ✅ 长期可维护的代码库

核心原则：**清晰的分层 → 低耦合 → 易维护 → 易扩展**
