const COMPLEX_TASK_PATTERN =
  /(研究|分析|生成|制作|写.*报告|做.*PPT|整理.*大纲|调研|总结.*并|查询.*并)/i;

const ADVISORY_THRESHOLD = 2;

const sessionAdvisoryState = new Map<string, { count: number; lastAdvisory: number }>();

const isMainSession = (sessionKey: unknown): boolean =>
  typeof sessionKey === "string" && sessionKey.startsWith("agent:main:");

const asString = (value: unknown): string => (typeof value === "string" ? value : "");

interface HookContext {
  bodyForAgent?: unknown;
  body?: unknown;
  content?: unknown;
}

interface HookEvent {
  type: string;
  action: string;
  sessionKey: unknown;
  context?: HookContext | null;
}

const handler = async (event: HookEvent): Promise<void> => {
  if (!event || event.type !== "message" || event.action !== "preprocessed") {
    return;
  }

  if (!isMainSession(event.sessionKey)) {
    return;
  }

  const context = event.context && typeof event.context === "object" ? event.context : null;
  if (!context) {
    return;
  }

  const bodyForAgent = asString(context.bodyForAgent);
  const body = asString(context.body);
  const content = asString(context.content);
  const source = bodyForAgent || body || content;

  if (!source) {
    return;
  }

  if (source.includes("[ROUTING-ADVISORY]") || source.includes("[ROUTING-GATE]")) {
    return;
  }

  const sessionId = asString(event.sessionKey);
  if (!sessionId) {
    return;
  }
  const state = sessionAdvisoryState.get(sessionId) || { count: 0, lastAdvisory: 0 };

  const isComplexTask = COMPLEX_TASK_PATTERN.test(source);
  const hasMultipleSteps = (source.match(/[，,。！!；;]+/g) || []).length >= 2;

  if ((isComplexTask || hasMultipleSteps) && state.count < ADVISORY_THRESHOLD) {
    state.count++;
    sessionAdvisoryState.set(sessionId, state);

    const advisory = [
      "[ROUTING-ADVISORY]",
      "This request involves multi-step work or synthesis.",
      `Advisory #${state.count}/${ADVISORY_THRESHOLD}: Consider using sessions_spawn with agentId='oe-orchestrator'`,
      "for better parallel execution and resource management.",
      "",
      "If you proceed in main, monitor tool usage and escalate if needed.",
    ].join("\n");

    (context as HookContext).bodyForAgent = `${advisory}\n\n---\n\nUser request:\n${source}`;
  }
};

export default handler;
