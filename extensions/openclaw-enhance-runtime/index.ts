// These tools are FORBIDDEN in the main session.
// Main should only route, read, and spawn subagents.
const MAIN_FORBIDDEN_TOOLS = new Set([
  "edit",
  "write",
  "exec", // bash is named exec internally
  "process",
  "browser",
  "playwright",
  "web_search",
  "web_fetch",
]);

// Track runIds that belong to the main session.
// When a before_tool_call fires, we check if its runId is a known main-session run.
const mainRunIds = new Set<string>();

export default {
  id: "oe-runtime",
  name: "openclaw-enhance-runtime",
  description: "Runtime integration bridge for OpenClaw Enhance",
  configSchema: {
    type: "object",
    additionalProperties: false,
    properties: {
      enableBridge: { type: "boolean" },
      logLevel: { type: "string", enum: ["debug", "info", "warn", "error"] }
    }
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register(api: any) {
    api.logger.info("oe-runtime: Registering tool execution gate");

    // Listen to agent events to track which runIds belong to the main agent.
    // The onAgentEvent callback receives events with sessionKey context.
    if (api.runtime?.events?.onAgentEvent) {
      api.runtime.events.onAgentEvent((event: { type: string; runId?: string; sessionKey?: string }) => {
        if (event.runId && typeof event.sessionKey === "string" && event.sessionKey.startsWith("agent:main:")) {
          mainRunIds.add(event.runId);
          // Prevent unbounded growth — keep only last 50 runs
          if (mainRunIds.size > 50) {
            const first = mainRunIds.values().next().value;
            if (first !== undefined) mainRunIds.delete(first);
          }
        }
      });
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    api.on("before_tool_call", async (context: any) => {
      try {
        const runId: unknown = context.runId;
        const toolName: unknown = context.toolName;

        const isMain = typeof runId === "string" && mainRunIds.has(runId);

        if (!isMain) {
          return;
        }

        if (typeof toolName === "string" && MAIN_FORBIDDEN_TOOLS.has(toolName)) {
          api.logger.warn(`oe-runtime: BLOCKED tool call [${toolName}] in main session (runId=${runId})`);

          return {
            block: true,
            blockReason: `CRITICAL RULE VIOLATION: The 'main' session is strictly FORBIDDEN from using the '${toolName}' tool to mutate files or execute commands directly.\n\nYou are a ROUTER. For any task that requires writing code, editing files, or running commands, you MUST use sessions_spawn({ agentId: "oe-orchestrator", task: "<description>" }) to delegate the work. Do not attempt to retry this tool.`
          };
        }
        return undefined;
      } catch (err) {
        // Fail-closed: if the handler crashes, block the tool call for safety.
        // This prevents main from bypassing the gate due to unexpected errors.
        api.logger.error(`oe-runtime: before_tool_call handler crashed, failing closed: ${err}`);
        return {
          block: true,
          blockReason: "oe-runtime encountered an internal error. Tool call blocked for safety. Use sessions_spawn({ agentId: \"oe-orchestrator\" }) to delegate this work."
        };
      }
    });
  }
};
