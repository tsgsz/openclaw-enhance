const isMainSession = (sessionKey: string): boolean =>
  sessionKey.startsWith("agent:main:");

// These tools are FORBIDDEN in the main session.
// Main should only route, read, and spawn subagents.
const MAIN_FORBIDDEN_TOOLS = new Set([
  "edit",
  "write",
  "exec", // bash is named exec internally
  "process",
  "browser",
  "playwright"
]);

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

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    api.on("before_tool_call", async (context: any) => {
      const sessionKey = context.sessionKey;
      
      // Only restrict the main session. Subagents (like opencode) can use any tool.
      if (!isMainSession(sessionKey)) {
        return;
      }

      const toolName = context.toolName;
      
      if (MAIN_FORBIDDEN_TOOLS.has(toolName)) {
        api.logger.warn(`oe-runtime: BLOCKED tool call [${toolName}] in main session`);
        
        return {
          block: true,
          blockReason: `CRITICAL RULE VIOLATION: The 'main' session is strictly FORBIDDEN from using the '${toolName}' tool to mutate files or execute commands directly.\n\nYou are a ROUTER. For any task that requires writing code, editing files, or running commands, you MUST use 'sessions_spawn' to delegate the work to the 'opencode' or 'worker' agent. Do not attempt to retry this tool.`
        };
      }
      return undefined;
    });
  }
};
