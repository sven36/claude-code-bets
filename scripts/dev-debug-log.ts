import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const projectRoot = join(__dirname, "..")
const debugLogPath = join(projectRoot, ".claude", "debug.inspect.log")

process.env.BUN_INSPECT = process.env.BUN_INSPECT || "localhost:8888/2dc3gzl5xot"
process.env.CLAUDE_CODE_DEBUG_LOG_LEVEL =
  process.env.CLAUDE_CODE_DEBUG_LOG_LEVEL || "verbose"
process.env.BUN_CONFIG_VERBOSE_FETCH = "node:http"

if (!process.argv.includes("--debug-file")) {
  process.argv.push("--debug-file", debugLogPath)
}

console.log(`Writing Claude debug logs to ${debugLogPath}`)

await import("./dev")
