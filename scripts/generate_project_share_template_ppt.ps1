param(
  [string]$TemplatePath = "C:\Users\dd\Pictures\前端行业前沿.pptx",
  [string]$OutputPath = "D:\work\claude-code-bets\Claude_Code_Best_源码分享_模板版_30min.pptx"
)

$ErrorActionPreference = "Stop"

function Set-TextRange {
  param(
    [object]$Shape,
    [string]$Text,
    [double]$FontSize = 24,
    [int]$Rgb = 0x000000,
    [bool]$Bold = $false
  )
  $Shape.TextFrame.TextRange.Text = $Text
  $Shape.TextFrame.TextRange.Font.Name = "Microsoft YaHei"
  $Shape.TextFrame.TextRange.Font.NameFarEast = "Microsoft YaHei"
  $Shape.TextFrame.TextRange.Font.Size = $FontSize
  $Shape.TextFrame.TextRange.Font.Color.RGB = $Rgb
  if ($Bold) { $Shape.TextFrame.TextRange.Font.Bold = -1 } else { $Shape.TextFrame.TextRange.Font.Bold = 0 }
}

function Get-TextShapes {
  param([object]$Shape)
  $result = @()
  if ($Shape.Type -eq 6) {
    for ($i = 1; $i -le $Shape.GroupItems.Count; $i++) {
      $result += Get-TextShapes $Shape.GroupItems.Item($i)
    }
  } else {
    try {
      if ($Shape.HasTextFrame -and $Shape.TextFrame.HasText) {
        $result += $Shape
      }
    } catch {}
  }
  return $result
}

function Insert-TemplateSlide {
  param(
    [object]$Presentation,
    [string]$TemplatePath,
    [int]$SourceIndex
  )
  $Presentation.Slides.InsertFromFile($TemplatePath, $Presentation.Slides.Count, $SourceIndex, $SourceIndex) | Out-Null
  return $Presentation.Slides.Item($Presentation.Slides.Count)
}

function New-TitleSlide {
  param(
    [object]$Presentation,
    [string]$TemplatePath,
    [string]$Title,
    [string]$Subtitle,
    [string]$Footer
  )
  $slide = Insert-TemplateSlide $Presentation $TemplatePath 1
  $texts = @()
  for ($i = 1; $i -le $slide.Shapes.Count; $i++) { $texts += Get-TextShapes $slide.Shapes.Item($i) }
  foreach ($shape in $texts) {
    $text = $shape.TextFrame.TextRange.Text
    if ($text -match "前端行业洞察") {
      Set-TextRange $shape $Title 54 0xE7EBFA $true
    } elseif ($text -match "探哲智能") {
      Set-TextRange $shape $Subtitle 17 0xFFFFFF $false
    } elseif ($text -match "汇报人") {
      Set-TextRange $shape $Footer 13 0xFFFFFF $false
    } elseif ($text -match "成为全球") {
      Set-TextRange $shape "Claude Code Best 源码导读 / 终端 Agent 运行时" 13 0xFFFFFF $false
    }
  }
}

function New-SectionSlide {
  param(
    [object]$Presentation,
    [string]$TemplatePath,
    [string]$No,
    [string]$Title,
    [string]$Subtitle
  )
  $slide = Insert-TemplateSlide $Presentation $TemplatePath 2
  $texts = @()
  for ($i = 1; $i -le $slide.Shapes.Count; $i++) { $texts += Get-TextShapes $slide.Shapes.Item($i) }
  foreach ($shape in $texts) {
    $text = $shape.TextFrame.TextRange.Text
    if ($text -match "行业前沿") {
      Set-TextRange $shape $Title 48 0x016DD9 $true
    } elseif ($text -match "Enter the directory") {
      Set-TextRange $shape $Subtitle 19 0x071D3A $false
    } elseif ($text -match "01") {
      Set-TextRange $shape $No 48 0xFFFFFF $true
    } elseif ($text -match "成为全球") {
      Set-TextRange $shape "Claude Code Best 源码导读" 10 0xFFFFFF $false
    }
  }
}

function Add-FlowText {
  param(
    [object]$Slide,
    [double]$Left,
    [double]$Top,
    [double]$Width,
    [double]$Height,
    [string]$Text,
    [double]$FontSize = 17
  )
  $box = $Slide.Shapes.AddTextbox(1, $Left, $Top, $Width, $Height)
  Set-TextRange $box $Text $FontSize 0x071D3A $false
  $box.TextFrame.MarginLeft = 8
  $box.TextFrame.MarginRight = 8
  $box.TextFrame.MarginTop = 6
  $box.TextFrame.MarginBottom = 6
  return $box
}

function Add-CodeBox {
  param(
    [object]$Slide,
    [double]$Left,
    [double]$Top,
    [double]$Width,
    [double]$Height,
    [string]$Text
  )
  $rect = $Slide.Shapes.AddShape(5, $Left, $Top, $Width, $Height)
  $rect.Fill.ForeColor.RGB = 0x071D3A
  $rect.Line.ForeColor.RGB = 0xE8E2D8
  $rect.TextFrame.TextRange.Text = $Text
  $rect.TextFrame.TextRange.Font.Name = "Consolas"
  $rect.TextFrame.TextRange.Font.Size = 13
  $rect.TextFrame.TextRange.Font.Color.RGB = 0xFFFFFF
  $rect.TextFrame.MarginLeft = 14
  $rect.TextFrame.MarginRight = 14
  $rect.TextFrame.MarginTop = 12
  $rect.TextFrame.MarginBottom = 12
  return $rect
}

function Add-ImageIfExists {
  param(
    [object]$Slide,
    [string]$Path,
    [double]$Left,
    [double]$Top,
    [double]$Width,
    [double]$Height
  )
  if (Test-Path -LiteralPath $Path) {
    $pic = $Slide.Shapes.AddPicture($Path, $false, $true, $Left, $Top, $Width, $Height)
    $pic.Line.ForeColor.RGB = 0xE8E2D8
    return $pic
  }
  return $null
}

function New-ContentSlide {
  param(
    [object]$Presentation,
    [string]$TemplatePath,
    [int]$TemplateIndex,
    [string]$Title,
    [string[]]$Bullets,
    [string]$Code = "",
    [string]$Image = ""
  )
  $slide = Insert-TemplateSlide $Presentation $TemplatePath $TemplateIndex
  $texts = @()
  for ($i = 1; $i -le $slide.Shapes.Count; $i++) { $texts += Get-TextShapes $slide.Shapes.Item($i) }
  $texts = $texts | Sort-Object { $_.Top }
  if ($texts.Count -gt 0) {
    Set-TextRange $texts[0] $Title 20 0x071D3A $true
  }
  if ($texts.Count -gt 1) {
    $body = ($Bullets | ForEach-Object { "• " + $_ }) -join "`r"
    if ($Code -or $Image) {
      $texts[1].Left = 64
      $texts[1].Top = 88
      $texts[1].Width = 410
      $texts[1].Height = 350
      Set-TextRange $texts[1] $body 20 0x000000 $false
    } else {
      Set-TextRange $texts[1] $body 24 0x000000 $false
    }
    $texts[1].TextFrame.MarginLeft = 6
    $texts[1].TextFrame.MarginRight = 6
    $texts[1].TextFrame.MarginTop = 4
    $texts[1].TextFrame.MarginBottom = 4
  }
  if ($Code) {
    Add-CodeBox $slide 505 102 360 300 $Code | Out-Null
  }
  if ($Image) {
    Add-ImageIfExists $slide $Image 500 95 360 310 | Out-Null
  }
}

function New-ThanksSlide {
  param(
    [object]$Presentation,
    [string]$TemplatePath
  )
  $slide = Insert-TemplateSlide $Presentation $TemplatePath 8
  $texts = @()
  for ($i = 1; $i -le $slide.Shapes.Count; $i++) { $texts += Get-TextShapes $slide.Shapes.Item($i) }
  foreach ($shape in $texts) {
    $text = $shape.TextFrame.TextRange.Text
    if ($text -match "THANKS") {
      Set-TextRange $shape "Q&A" 88 0xE7EBFA $true
    } elseif ($text -match "成为全球") {
      Set-TextRange $shape "Claude Code Best：终端 Agent 运行时源码分享" 13 0xFFFFFF $false
    }
  }
  Add-FlowText $slide 62 335 650 78 "讨论方向：内部工具走 Tool 还是 MCP？新 Provider 最小适配点在哪里？权限模型和压缩策略是否满足长任务？" 18 | Out-Null
}

$slides = @(
  @{Kind="title"; Title="Claude Code Best"; Subtitle="源码项目分享：从 CLI 到 Agent 运行时"; Footer="30 分钟技术分享 / 基于 PROJECT_SHARE_SPEECH_30MIN.md"},
  @{Kind="content"; Template=3; Title="分享目标与主线"; Bullets=@("用 30 分钟建立项目整体架构、核心链路和二次开发入口的共同认知", "不逐行讲代码，而是抓住从 CLI 到 Tool/API 的运行主线", "核心观点：它是终端 Agent 平台，不是普通聊天 CLI"); Code="CLI 启动`r  -> REPL / headless`r  -> QueryEngine`r  -> query.ts Agentic Loop`r  -> Tool 系统`r  -> API Provider"},
  @{Kind="content"; Template=5; Title="项目定位：终端 Agent 运行时"; Bullets=@("模型可以读文件、改文件、执行命令、调用 MCP、创建子 Agent", "系统维护多轮会话、上下文、记忆、transcript、成本和中断", "所有真实动作都要被权限系统、Hook、Plan Mode 和 UI 状态管理起来")},
  @{Kind="section"; No="01"; Title="工程地图"; Subtitle="技术栈、仓库结构与分层架构"},
  @{Kind="content"; Template=7; Title="技术栈与顶层结构"; Bullets=@("Bun + TypeScript/TSX 单仓库，主应用源码集中在 src/", "React/Ink 渲染终端 UI，Commander.js 负责 CLI 路由", "Zod / JSON Schema 约束模型传来的工具参数", "services/api 支持 Claude 主实现和 OpenAI/Gemini/Grok 适配"); Code="src/        主应用源码`rpackages/   workspace 子包`rdocs/       文档和架构说明`rtests/      集成测试和 mocks`rscripts/    开发、构建、健康检查"},
  @{Kind="content"; Template=3; Title="七层架构总览"; Bullets=@("CLI Bootstrap：快速路径和特殊模式", "main.tsx：配置、认证、命令、运行模式分发", "REPL/headless：不同前端，共用核心", "QueryEngine：会话级编排；query.ts：Agentic Loop"); Image="docs\images\architecture-layers.png"},
  @{Kind="content"; Template=5; Title="启动与路由"; Bullets=@("cli.tsx 先处理 --version、MCP、daemon、bridge 等轻路径", "常规路径才动态 import main.tsx，降低短命令冷启动成本", "main.tsx 组织配置、认证、feature flags、MCP、插件、skills、tools、commands", "最终分发到 REPL、headless、resume、remote/bridge 等路径")},
  @{Kind="section"; No="02"; Title="核心链路"; Subtitle="QueryEngine 与 query.ts Agentic Loop"},
  @{Kind="content"; Template=7; Title="UI 与会话编排"; Bullets=@("REPL.tsx 负责输入、消息列表、权限弹窗、状态栏、任务面板", "src/cli 支撑 print、structured IO、headless 输出", "QueryEngine 维护 mutableMessages、readFileState、permissionDenials、totalUsage、transcript、abortController", "UI 和 SDK 输入最终都被转成 query() 可消费的参数")},
  @{Kind="content"; Template=3; Title="Agentic Loop：为什么不是聊天 CLI"; Bullets=@("普通聊天：用户输入 -> 模型回答 -> 结束", "Coding Agent：模型发出 tool_use，系统执行真实动作并写回 tool_result", "模型根据真实反馈继续读文件、改文件、运行测试，直到任务结束"); Image="docs\images\agentic-loop.png"},
  @{Kind="content"; Template=5; Title="query.ts 的五步循环"; Bullets=@("上下文预处理：预算、snip、microcompact、context collapse、auto compact", "流式调用模型，接收普通文本和 tool_use", "执行工具：并发安全则并行，有副作用则串行", "tool_result 作为新消息写回，再进入下一轮模型调用", "处理 prompt too long、max output tokens、fallback、stop hook 等恢复路径"); Image="docs\images\streaming-timeline.png"},
  @{Kind="section"; No="03"; Title="真实执行"; Subtitle="工具系统、权限边界与模型 Provider"},
  @{Kind="content"; Template=7; Title="工具系统：Tool as Capability"; Bullets=@("Tool.ts 定义工具接口、权限上下文、工具结果、进度类型", "tools.ts 根据 feature flag、环境变量、权限规则、MCP、插件组装工具列表", "具体工具包括 Bash、PowerShell、FileRead、FileEdit、Glob/Grep、Agent、MCP、WebSearch、LSP、Todo、Skill", "工具不是简单函数，而是带 schema、权限、并发语义和结果限制的能力对象")},
  @{Kind="content"; Template=3; Title="权限边界：模型只提出意图"; Bullets=@("输入先过 schema 校验，再进入工具自身权限检查", "allow / ask / deny 规则、Hook、Plan Mode、UI/headless callback 共同裁决", "文件路径、Bash/PowerShell 命令、MCP 调用都必须在执行前被拦住或放行", "核心思想：模型提出意图，权限系统决定边界，工具系统负责执行"); Image="docs\images\permission-layers.png"},
  @{Kind="content"; Template=5; Title="API Provider 适配"; Bullets=@("services/api/claude.ts 是 Claude 主实现", "openai、gemini、grok 目录负责协议适配", "关键适配点：消息转换、工具转换、stream adapter、model mapping", "query.ts 依赖统一 streaming 事件，不直接绑定某个 Provider"); Image="docs\images\data-flow.png"},
  @{Kind="section"; No="04"; Title="长任务能力"; Subtitle="上下文、记忆、压缩与扩展入口"},
  @{Kind="content"; Template=7; Title="上下文、记忆与压缩"; Bullets=@("System Prompt、userContext、toolUseContext 统一组装项目环境和工具说明", "CLAUDE.md、项目记忆、session memory、nested memory 支撑长期上下文", "tokens/tokenBudget 估算上下文长度和输出预算", "autoCompact、reactiveCompact、contextCollapse、microcompact 控制窗口压力", "过长工具结果可落盘，只把预览和路径给模型"); Image="docs\images\compaction.png"},
  @{Kind="content"; Template=3; Title="扩展体系与二次开发入口"; Bullets=@("新增 slash command：src/commands/、src/commands.ts、src/types/command.ts", "新增工具：src/Tool.ts、src/tools.ts、src/tools/*，优先参考 FileEditTool 或 BashTool", "新增模型 Provider：src/services/api/，参考 openai/gemini/grok", "MCP/Plugins/Skills：services/mcp、utils/plugins、src/skills、SkillTool", "改 UI、权限、压缩分别看 screens/hooks、utils/permissions、services/compact"); Image="docs\images\mcp-architecture.png"},
  @{Kind="content"; Template=5; Title="源码阅读路线"; Bullets=@("第一轮只读主链路：package/build -> cli.tsx -> main.tsx -> REPL/headless -> QueryEngine -> query.ts", "第二轮选一个工具深入：FileEditTool 或 BashTool，看 schema、权限和结果展示", "第三轮读 Provider 适配和上下文压缩，这是长任务稳定性的关键"); Code="核心主线`rsrc/entrypoints/cli.tsx`r  -> src/main.tsx`r  -> REPL.tsx / src/cli`r  -> QueryEngine.ts`r  -> query.ts`r  -> Tool.ts + tools.ts + tools/"},
  @{Kind="content"; Template=7; Title="总结"; Bullets=@("复杂 CLI：启动性能、跨平台、终端渲染、快捷键、headless 输出", "复杂 Agent：多轮循环、工具调用、上下文压缩、错误恢复、成本追踪", "平台化能力：MCP、插件、Skills、子 Agent、远程控制、多 Provider、feature flags", "一句话：Claude Code Best 是一套终端 Agent 运行时")},
  @{Kind="thanks"}
)

$pp = $null
$pres = $null
try {
  $templateResolved = (Resolve-Path -LiteralPath $TemplatePath).Path
  $pp = New-Object -ComObject PowerPoint.Application
  $pres = $pp.Presentations.Add(0)
  $pres.PageSetup.SlideWidth = 960
  $pres.PageSetup.SlideHeight = 540

  foreach ($item in $slides) {
    switch ($item.Kind) {
      "title" { New-TitleSlide $pres $templateResolved $item.Title $item.Subtitle $item.Footer }
      "section" { New-SectionSlide $pres $templateResolved $item.No $item.Title $item.Subtitle }
      "content" {
        $imagePath = ""
        if ($item.ContainsKey("Image") -and $item.Image) { $imagePath = Join-Path (Get-Location) $item.Image }
        $codeText = ""
        if ($item.ContainsKey("Code")) { $codeText = $item.Code }
        New-ContentSlide $pres $templateResolved $item.Template $item.Title $item.Bullets $codeText $imagePath
      }
      "thanks" { New-ThanksSlide $pres $templateResolved }
    }
  }

  $resolvedOut = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
  $pres.SaveAs($resolvedOut, 24)
  Write-Output $resolvedOut
} finally {
  if ($pres) { try { $pres.Close() } catch {} }
  if ($pp) { try { $pp.Quit() } catch {} }
}
