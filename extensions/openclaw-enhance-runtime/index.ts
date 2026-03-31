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

const asString = (value: unknown): string => (typeof value === "string" ? value : "");

const normalizeSessionKey = (sessionKey: unknown): string => {
  if (typeof sessionKey === "string") return sessionKey;
  if (sessionKey && typeof sessionKey === "object") {
    const candidate = sessionKey as Record<string, unknown>;
    return asString(candidate.sessionKey || candidate.session_key || candidate.key || candidate.id);
  }
  return "";
};

const isMainSession = (sessionKey: unknown): boolean => {
  const key = normalizeSessionKey(sessionKey);
  return key === "main" || key.startsWith("agent:main:");
};

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
      api.runtime.events.onAgentEvent((event: { type: string; runId?: string; sessionKey?: unknown; toolName?: string; params?: Record<string, unknown> }) => {
        if (event.runId && isMainSession(event.sessionKey)) {
          mainRunIds.add(event.runId);
          // Prevent unbounded growth — keep only last 50 runs
          if (mainRunIds.size > 50) {
            const first = mainRunIds.values().next().value;
            if (first !== undefined) mainRunIds.delete(first);
          }
        }

        if (event.toolName === "sessions_spawn" && event.params && typeof event.params === "object") {
          const agentId = event.params.agentId;
          if (typeof agentId === "string" && agentId !== "oe-orchestrator") {
            api.logger.warn(`oe-runtime: sessions_spawn from main should target oe-orchestrator first (agentId=${agentId})`);
          }
        }
      });
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    api.on("before_tool_call", async (context: any) => {
      const runIdForFailClosed: unknown = context?.runId;
      const isMainForFailClosed = typeof runIdForFailClosed === "string" && mainRunIds.has(runIdForFailClosed);
      try {
        const runId: unknown = context.runId;
        const toolName: unknown = context.toolName;
        const sessionKey: unknown = context.sessionKey;

        const isMain =
          (typeof runId === "string" && mainRunIds.has(runId)) ||
          isMainSession(sessionKey);

        if (!isMain) {
          return;
        }

        if (typeof toolName === "string" && MAIN_FORBIDDEN_TOOLS.has(toolName)) {
          api.logger.warn(`oe-runtime: BLOCKED tool call [${toolName}] in main session (runId=${runId})`);

          return {
            block: true,
            blockReason: `CRITICAL RULE VIOLATION: The 'main' session is strictly FORBIDDEN from using the '${toolName}' tool to mutate files or execute commands directly.\n\nYou are a ROUTER. For any task that requires writing code, editing files, or running commands, you MUST use sessions_spawn({ agentId: "oe-orchestrator", ... }) to delegate the work. Do not attempt to retry this tool.`
          };
        }
        return undefined;
      } catch (err) {
        if (!isMainForFailClosed) {
          api.logger.error(`oe-runtime: before_tool_call handler crashed for non-main run, allowing: ${err}`);
          return undefined;
        }

        api.logger.error(`oe-runtime: before_tool_call handler crashed in main session, failing closed: ${err}`);
        return {
          block: true,
          blockReason: "oe-runtime encountered an internal error. Tool call blocked for safety. Use sessions_spawn({ agentId: \"oe-orchestrator\", ... }) to delegate this work."
        };
      }
    });
  }
};
