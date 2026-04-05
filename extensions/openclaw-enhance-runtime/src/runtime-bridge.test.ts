/**
 * Tests for Runtime Bridge
 *
 * Uses Node.js built-in test runner (node --test)
 */

import { describe, it } from "node:test";
import assert from "node:assert";
import {
  RuntimeBridge,
  createRuntimeBridge,
  type SpawnEvent,
} from "./runtime-bridge.js";
import { enrichSpawnEvent } from "../../../hooks/oe-subagent-spawn-enrich/handler.js";
import * as RuntimeBridgeModule from "./runtime-bridge.js";

describe("RuntimeBridge", () => {
  describe("constructor", () => {
    it("should create with default config", () => {
      const bridge = new RuntimeBridge();
      const config = bridge.getConfig();

      assert.strictEqual(config.enabled, true);
      assert.strictEqual(config.namespace, "oe");
      assert.strictEqual(config.logLevel, "info");
    });

    it("should create with custom config", () => {
      const bridge = new RuntimeBridge({
        enabled: false,
        namespace: "custom",
        logLevel: "debug",
      });
      const config = bridge.getConfig();

      assert.strictEqual(config.enabled, false);
      assert.strictEqual(config.namespace, "custom");
      assert.strictEqual(config.logLevel, "debug");
    });
  });

  describe("createRuntimeBridge", () => {
    it("should create bridge with factory function", () => {
      const bridge = createRuntimeBridge({ namespace: "test" });
      assert.ok(bridge instanceof RuntimeBridge);
      assert.strictEqual(bridge.getConfig().namespace, "test");
    });
  });

  describe("handleSpawnEvent", () => {
    it("should process enriched spawn event", () => {
      const bridge = new RuntimeBridge();
      const event: SpawnEvent = {
        event: "subagent_spawning",
        timestamp: new Date().toISOString(),
        payload: {
          subagent_type: "oe-orchestrator",
          task_description: "Test task",
          task_id: "task_test_123",
          project: "test-project",
          parent_session: "sess_parent_001",
          eta_bucket: "medium",
          dedupe_key: "test:oe:testhash:20240115",
        },
        context: {
          session_id: "sess_001",
        },
      };

      const result = bridge.handleSpawnEvent(event);

      assert.strictEqual(result, true);
      assert.strictEqual(bridge.getActiveTasks().length, 1);
    });

    it("should reject event when bridge is disabled", () => {
      const bridge = new RuntimeBridge({ enabled: false });
      const event: SpawnEvent = {
        event: "subagent_spawning",
        timestamp: new Date().toISOString(),
        payload: {
          subagent_type: "oe-orchestrator",
          task_description: "Test task",
          task_id: "task_test_123",
          project: "test-project",
          parent_session: "sess_parent_001",
          eta_bucket: "medium",
          dedupe_key: "test:oe:testhash:20240115",
        },
        context: {
          session_id: "sess_001",
        },
      };

      const result = bridge.handleSpawnEvent(event);

      assert.strictEqual(result, false);
    });

    it("should warn on missing task_id enrichment", () => {
      const bridge = new RuntimeBridge();
      const event: SpawnEvent = {
        event: "subagent_spawning",
        timestamp: new Date().toISOString(),
        payload: {
          subagent_type: "oe-orchestrator",
          task_description: "Test task",
          // Missing task_id
        },
        context: {
          session_id: "sess_001",
        },
      };

      const result = bridge.handleSpawnEvent(event);

      assert.strictEqual(result, false);
    });
  });

  describe("getTask", () => {
    it("should retrieve tracked task by ID", () => {
      const bridge = new RuntimeBridge();
      const event: SpawnEvent = {
        event: "subagent_spawning",
        timestamp: new Date().toISOString(),
        payload: {
          subagent_type: "oe-orchestrator",
          task_description: "Test task",
          task_id: "task_test_123",
          project: "test-project",
          parent_session: "sess_parent_001",
          eta_bucket: "short",
          dedupe_key: "test:oe:testhash:20240115",
        },
        context: {
          session_id: "sess_001",
        },
      };

      bridge.handleSpawnEvent(event);
      const task = bridge.getTask("task_test_123");

      assert.ok(task);
      assert.strictEqual(task?.task_id, "task_test_123");
      assert.strictEqual(task?.project, "test-project");
      assert.strictEqual(task?.eta_bucket, "short");
    });

    it("should return undefined for unknown task", () => {
      const bridge = new RuntimeBridge();
      const task = bridge.getTask("nonexistent");

      assert.strictEqual(task, undefined);
    });
  });

  describe("completeTask", () => {
    it("should remove completed task from tracking", () => {
      const bridge = new RuntimeBridge();
      const event: SpawnEvent = {
        event: "subagent_spawning",
        timestamp: new Date().toISOString(),
        payload: {
          subagent_type: "oe-orchestrator",
          task_description: "Test task",
          task_id: "task_test_123",
          project: "test-project",
          parent_session: "sess_parent_001",
          eta_bucket: "medium",
          dedupe_key: "test:oe:testhash:20240115",
        },
        context: {
          session_id: "sess_001",
        },
      };

      bridge.handleSpawnEvent(event);
      assert.strictEqual(bridge.getActiveTasks().length, 1);

      const result = bridge.completeTask("task_test_123");

      assert.strictEqual(result, true);
      assert.strictEqual(bridge.getActiveTasks().length, 0);
    });

    it("should return false for unknown task", () => {
      const bridge = new RuntimeBridge();
      const result = bridge.completeTask("nonexistent");

      assert.strictEqual(result, false);
    });
  });

  describe("isDuplicate", () => {
    it("should detect duplicate based on dedupe key", () => {
      const bridge = new RuntimeBridge();
      const event: SpawnEvent = {
        event: "subagent_spawning",
        timestamp: new Date().toISOString(),
        payload: {
          subagent_type: "oe-orchestrator",
          task_description: "Test task",
          task_id: "task_test_123",
          project: "test-project",
          parent_session: "sess_parent_001",
          eta_bucket: "medium",
          dedupe_key: "test:oe:unique:20240115",
        },
        context: {
          session_id: "sess_001",
        },
      };

      bridge.handleSpawnEvent(event);

      assert.strictEqual(bridge.isDuplicate("test:oe:unique:20240115"), true);
      assert.strictEqual(bridge.isDuplicate("test:oe:different:20240115"), false);
    });
  });

  describe("updateConfig", () => {
    it("should update configuration partially", () => {
      const bridge = new RuntimeBridge();

      bridge.updateConfig({ logLevel: "debug" });

      const config = bridge.getConfig();
      assert.strictEqual(config.logLevel, "debug");
      assert.strictEqual(config.enabled, true); // Unchanged
      assert.strictEqual(config.namespace, "oe"); // Unchanged
    });
  });

  describe("sanitizeEnhanceOutwardText", () => {
    it("should strip known leaked internal markers from outward text", () => {
      const input =
        "alpha [Pasted ~1 lines] beta <|tool_calls_section_begin|><|tool_call_begin|>gamma<|tool_call_end|><|tool_calls_section_end|> delta";

      const result = (RuntimeBridgeModule as { sanitizeEnhanceOutwardText?: (
        value: string,
      ) => string }).sanitizeEnhanceOutwardText?.(input);

      assert.strictEqual(result, "alpha beta gamma delta");
    });

    it("should preserve ordinary prose unchanged", () => {
      const input = "The quick brown fox jumps over the lazy dog.";

      const result = (RuntimeBridgeModule as { sanitizeEnhanceOutwardText?: (
        value: string,
      ) => string }).sanitizeEnhanceOutwardText?.(input);

      assert.strictEqual(result, input);
    });
  });

  describe("getActiveTasks", () => {
    it("should return empty array when no tasks", () => {
      const bridge = new RuntimeBridge();
      const tasks = bridge.getActiveTasks();

      assert.deepStrictEqual(tasks, []);
    });

    it("should return all active tasks", () => {
      const bridge = new RuntimeBridge();

      const event1: SpawnEvent = {
        event: "subagent_spawning",
        timestamp: new Date().toISOString(),
        payload: {
          subagent_type: "oe-orchestrator",
          task_description: "Task 1",
          task_id: "task_001",
          project: "project-a",
          parent_session: "sess_001",
          eta_bucket: "short",
          dedupe_key: "pa:oe:h1:20240115",
        },
        context: { session_id: "sess_001" },
      };

      const event2: SpawnEvent = {
        event: "subagent_spawning",
        timestamp: new Date().toISOString(),
        payload: {
          subagent_type: "oe-searcher",
          task_description: "Task 2",
          task_id: "task_002",
          project: "project-b",
          parent_session: "sess_002",
          eta_bucket: "long",
          dedupe_key: "pb:oe:h2:20240115",
        },
        context: { session_id: "sess_002" },
      };

      bridge.handleSpawnEvent(event1);
      bridge.handleSpawnEvent(event2);

      const tasks = bridge.getActiveTasks();

      assert.strictEqual(tasks.length, 2);
      assert.ok(tasks.some((t) => t.task_id === "task_001"));
      assert.ok(tasks.some((t) => t.task_id === "task_002"));
    });
  });
});

describe("oe-runtime tool gate (index.ts)", () => {
  const createMockApi = () => {
    const logs: { level: string; msg: string }[] = [];
    let agentEventCallback: ((event: {
      type: string;
      runId?: string;
      sessionKey?: unknown;
      toolName?: string;
      params?: Record<string, unknown>;
    }) => void) | null = null;
    return {
      logger: {
        info: (msg: string) => logs.push({ level: "info", msg }),
        warn: (msg: string) => logs.push({ level: "warn", msg }),
        error: (msg: string) => logs.push({ level: "error", msg }),
      },
      runtime: {
        events: {
          onAgentEvent: (cb: (event: {
            type: string;
            runId?: string;
            sessionKey?: unknown;
            toolName?: string;
            params?: Record<string, unknown>;
          }) => void) => { agentEventCallback = cb; },
        },
      },
      logs,
      handlers: new Map<string, (context: Record<string, unknown>) => Promise<unknown>>(),
      on(event: string, handler: (context: Record<string, unknown>) => Promise<unknown>) {
        this.handlers.set(event, handler);
      },
      simulateAgentEvent(event: {
        type: string;
        runId?: string;
        sessionKey?: unknown;
        toolName?: string;
        params?: Record<string, unknown>;
      }) {
        if (agentEventCallback) agentEventCallback(event);
      },
    };
  };

  const loadPlugin = async () => {
    const mod = await import("../index.js");
    return mod.default;
  };

  const registerMainRun = (api: ReturnType<typeof createMockApi>, runId: string) => {
    api.simulateAgentEvent({ type: "run_start", runId, sessionKey: "agent:main:main" });
  };

  describe("runId-based session identification", () => {
    it("should only track valid main session keys", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      const handler = api.handlers.get("before_tool_call")!;

      const cases: Array<{ label: string; sessionKey: unknown; shouldBlock: boolean }> = [
        { label: "undefined", sessionKey: undefined, shouldBlock: false },
        { label: "null", sessionKey: null, shouldBlock: false },
        { label: "empty", sessionKey: "", shouldBlock: false },
        { label: "non-main", sessionKey: "agent:oe-orchestrator:subagent:123", shouldBlock: false },
        { label: "valid-main", sessionKey: "agent:main:main", shouldBlock: true },
      ];

      for (const { label, sessionKey, shouldBlock } of cases) {
        const runId = `run-${label}`;
        api.simulateAgentEvent({ type: "run_start", runId, sessionKey });

        const result = await handler({ runId, toolName: "edit" });
        if (shouldBlock) {
          assert.ok(result, `Expected main session to block for ${label}`);
          assert.strictEqual((result as { block: boolean }).block, true);
        } else {
          assert.strictEqual(result, undefined, `Expected non-main session key to stay unblocked for ${label}`);
        }
      }
    });

    it("should treat plain main sessionKey as main and block forbidden tools", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      api.simulateAgentEvent({ type: "run_start", runId: "main-run-plain", sessionKey: "main" });
      const handler = api.handlers.get("before_tool_call")!;

      const result = await handler({ runId: "main-run-plain", toolName: "edit" }) as { block: boolean } | undefined;
      assert.ok(result);
      assert.strictEqual((result as { block: boolean }).block, true);
    });

    it("should not block when runId is unknown (not registered as main)", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      const handler = api.handlers.get("before_tool_call")!;

      const result = await handler({ runId: "unknown-run", toolName: "edit" });
      assert.strictEqual(result, undefined);
    });

    it("should not block when runId is undefined", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      const handler = api.handlers.get("before_tool_call")!;

      const result = await handler({ runId: undefined, toolName: "edit" });
      assert.strictEqual(result, undefined);
    });

    it("should block forbidden tool when runId is registered as main", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      registerMainRun(api, "main-run-1");
      const handler = api.handlers.get("before_tool_call")!;

      const result = await handler({ runId: "main-run-1", toolName: "edit" }) as { block: boolean; blockReason?: string } | undefined;
      assert.ok(result);
      assert.strictEqual((result as { block: boolean }).block, true);
    });

    it("should fail closed for a known main-session run when the handler throws", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      registerMainRun(api, "main-run-1");
      const handler = api.handlers.get("before_tool_call")!;

      const poisonContext = new Proxy({}, {
        get(_, prop) {
          if (prop === "runId") return "main-run-1";
          if (prop === "toolName") throw new Error("simulated crash");
          return undefined;
        }
      });

      const result = await handler(poisonContext);
      assert.ok(result);
      assert.strictEqual((result as { block: boolean }).block, true);
      assert.ok((result as { blockReason: string }).blockReason.includes("oe-orchestrator"));
      assert.ok((result as { blockReason: string }).blockReason.includes("sessions_spawn"));
      assert.ok(api.logs.some((log) => log.level === "error" && log.msg.includes("failing closed")));
    });

    it("should allow subagent runId to use forbidden tools", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      registerMainRun(api, "main-run-1");
      api.simulateAgentEvent({ type: "run_start", runId: "subagent-run-1", sessionKey: "agent:oe-orchestrator:abc" });
      const handler = api.handlers.get("before_tool_call")!;

      const result = await handler({ runId: "subagent-run-1", toolName: "edit" });
      assert.strictEqual(result, undefined);
    });
  });

  describe("Task 4: session identity guardrails", () => {
    it("should reject ambiguous object-shaped session keys as unsafe instead of silently falling back", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      const handler = api.handlers.get("before_tool_call")!;

      const ambiguousKey = { id: "main" };
      const runId = "ambiguous-run";
      
      api.simulateAgentEvent({ type: "run_start", runId, sessionKey: ambiguousKey });

      const result = await handler({ runId, toolName: "edit" });
      
      assert.strictEqual(result, undefined, "Ambiguous object keys should not be trusted as main sessions");
    });

    it("should preserve canonical main session recognition for 'main' and 'agent:main:*' forms", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      const handler = api.handlers.get("before_tool_call")!;

      const canonicalKeys = ["main", "agent:main:123", "agent:main:xyz"];
      
      for (const key of canonicalKeys) {
        const runId = `canonical-${key}`;
        api.simulateAgentEvent({ type: "run_start", runId, sessionKey: key });

        const result = await handler({ runId, toolName: "edit" }) as { block: boolean } | undefined;
        assert.ok(result, `Canonical key ${key} should be recognized as main`);
        assert.strictEqual(result.block, true);
      }
    });
  });

  describe("fail-closed behavior", () => {
    it("should block when handler encounters unexpected error", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      registerMainRun(api, "main-run-1");
      const handler = api.handlers.get("before_tool_call")!;

      const poisonContext = new Proxy({}, {
        get(_, prop) {
          if (prop === "runId") return "main-run-1";
          if (prop === "toolName") throw new Error("simulated crash");
          return undefined;
        }
      });

      const result = await handler(poisonContext);
      assert.ok(result);
      assert.strictEqual((result as { block: boolean }).block, true);
      assert.ok((result as { blockReason: string }).blockReason.includes("internal error"));
    });
  });

  describe("blockReason routing guidance", () => {
    it("should recommend oe-orchestrator in blockReason", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      registerMainRun(api, "main-run-1");
      const handler = api.handlers.get("before_tool_call")!;

      const result = await handler({ runId: "main-run-1", toolName: "edit" }) as { block: boolean; blockReason?: string } | undefined;
      assert.ok(result);
      assert.ok((result as { blockReason: string }).blockReason.includes("oe-orchestrator"));
      assert.ok((result as { blockReason: string }).blockReason.includes("sessions_spawn"));
    });

    it("should recommend oe-orchestrator in fail-closed blockReason", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      registerMainRun(api, "main-run-1");
      const handler = api.handlers.get("before_tool_call")!;

      const poisonContext = new Proxy({}, {
        get(_, prop) {
          if (prop === "runId") return "main-run-1";
          if (prop === "toolName") throw new Error("boom");
          return undefined;
        }
      });

      const result = await handler(poisonContext);
      assert.ok(result);
      assert.ok((result as { blockReason: string }).blockReason.includes("oe-orchestrator"));
    });
  });

  describe("sessions_spawn routing metadata", () => {
    it("should inspect agentId rather than agent when warning on non-orchestrator spawn targets", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);

      api.simulateAgentEvent({
        type: "tool_call",
        runId: "main-run-1",
        sessionKey: "agent:main:main",
        toolName: "sessions_spawn",
        params: {
          agent: "oe-searcher",
          agentId: "oe-orchestrator",
        },
      });

      assert.strictEqual(api.logs.some((log) => log.level === "warn"), false);
    });

    it("should warn when sessions_spawn agentId is not oe-orchestrator", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);

      api.simulateAgentEvent({
        type: "tool_call",
        runId: "main-run-1",
        sessionKey: "agent:main:main",
        toolName: "sessions_spawn",
        params: {
          agent: "oe-orchestrator",
          agentId: "oe-searcher",
        },
      });

      assert.ok(api.logs.some((log) => log.level === "warn" && log.msg.includes("agentId=oe-searcher")));
    });
  });

  describe("forbidden tools enforcement", () => {
    it("should block all forbidden tools in main session", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      registerMainRun(api, "main-run-1");
      const handler = api.handlers.get("before_tool_call")!;

      const forbidden = ["edit", "write", "exec", "process", "browser", "playwright", "web_search", "web_fetch"];
      for (const tool of forbidden) {
        const result = await handler({ runId: "main-run-1", toolName: tool });
        assert.ok(result, `Expected block for tool: ${tool}`);
        assert.strictEqual((result as { block: boolean }).block, true, `Expected block=true for tool: ${tool}`);
      }
    });

    it("should allow non-forbidden tools in main session", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      registerMainRun(api, "main-run-1");
      const handler = api.handlers.get("before_tool_call")!;

      const result = await handler({ runId: "main-run-1", toolName: "sessions_spawn" });
      assert.strictEqual(result, undefined);
    });
  });

  describe("Task 12: Sanitizer integration at enhance-controlled outward boundaries", () => {
    it("should sanitize blockReason when blocking forbidden tools", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      registerMainRun(api, "main-run-sanitizer");
      const handler = api.handlers.get("before_tool_call")!;

      const result = await handler({ runId: "main-run-sanitizer", toolName: "edit" }) as { block: boolean; blockReason?: string } | undefined;
      
      assert.ok(result);
      assert.strictEqual(result.block, true);
      // The blockReason should not contain any internal markers after sanitization
      assert.ok(!result.blockReason?.includes("[Pasted ~"), "blockReason should not contain pasted markers");
      // But it should still contain the essential message
      assert.ok(result.blockReason?.includes("CRITICAL RULE VIOLATION"), "blockReason should contain the warning message");
      assert.ok(result.blockReason?.includes("oe-orchestrator"), "blockReason should mention oe-orchestrator");
    });

    it("should sanitize fail-closed blockReason", async () => {
      const api = createMockApi();
      const plugin = await loadPlugin();
      plugin.register(api);
      registerMainRun(api, "main-run-fail-closed");
      const handler = api.handlers.get("before_tool_call")!;

      const poisonContext = new Proxy({}, {
        get(_, prop) {
          if (prop === "runId") return "main-run-fail-closed";
          if (prop === "toolName") throw new Error("simulated crash");
          return undefined;
        }
      });

      const result = await handler(poisonContext) as { block: boolean; blockReason?: string } | undefined;
      
      assert.ok(result);
      assert.strictEqual(result.block, true);
      // Should not contain pasted markers
      assert.ok(!result.blockReason?.includes("[Pasted ~"), "fail-closed blockReason should not contain pasted markers");
      // Should contain the error message
      assert.ok(result.blockReason?.includes("internal error"), "fail-closed blockReason should mention internal error");
    });
  });
});

describe("Integration: Hook and Bridge", () => {
  it("should handle events from oe-subagent-spawn-enrich hook format", () => {
    const bridge = new RuntimeBridge();

    // Simulate event as it would come from the hook
    const hookEvent: SpawnEvent = {
      event: "subagent_spawning",
      timestamp: new Date().toISOString(),
      payload: {
        subagent_type: "oe-orchestrator",
        task_description: "Refactor auth module",
        estimated_toolcalls: 5,
        estimated_duration_minutes: 15,
        // Enriched fields from hook
        task_id: "task_abc123_xyz789",
        project: "my-project",
        parent_session: "sess_parent_001",
        eta_bucket: "medium",
        dedupe_key: "my-project:oe-orchestrator:auth-ref:20240115",
      },
      context: {
        session_id: "sess_parent_001",
        project: "my-project",
      },
    };

    const result = bridge.handleSpawnEvent(hookEvent);
    assert.strictEqual(result, true);

    const task = bridge.getTask("task_abc123_xyz789");
    assert.ok(task);
    assert.strictEqual(task?.project, "my-project");
    assert.strictEqual(task?.eta_bucket, "medium");
    assert.strictEqual(
      task?.dedupe_key,
      "my-project:oe-orchestrator:auth-ref:20240115",
    );
  });

  it("should reject or mark ambiguous restart ownership unsafe instead of silently falling back", () => {
    const restartInput = {
      event: "subagent_spawning",
      payload: {
        subagent_type: "oe-orchestrator",
        task_description: "Resume the interrupted handoff",
      },
      context: {
        session_id: "sess_restart_001",
        project: "default",
        restart_epoch: 9,
      },
    } as Parameters<typeof enrichSpawnEvent>[0];

    type UnsafeEnrichResult = ReturnType<typeof enrichSpawnEvent> & {
      unsafe?: boolean;
      enriched_payload: ReturnType<typeof enrichSpawnEvent>["enriched_payload"] & {
        ownership_status?: string;
      };
    };

    let threw = false;
    let result: UnsafeEnrichResult | undefined;

    try {
      result = enrichSpawnEvent(restartInput) as UnsafeEnrichResult;
    } catch {
      threw = true;
    }

    assert.ok(
      threw ||
        result?.unsafe === true ||
        result?.enriched_payload.ownership_status === "unsafe_ambiguous_restart",
      "ambiguous restart ownership should be rejected or explicitly marked unsafe",
    );
  });

  it("should keep dedupe identity distinct for channel-distinct ownership on the same task payload", () => {
    const feishuResult = enrichSpawnEvent({
      event: "subagent_spawning",
      payload: {
        subagent_type: "oe-orchestrator",
        task_description: "Resume shared task payload",
      },
      context: {
        session_id: "sess_same_lineage",
        parent_session: "sess_same_lineage",
        project: "project-guardrail",
        ownership: {
          channel_type: "feishu",
          channel_conversation_id: "conv-feishu-001",
        },
      },
    } as Parameters<typeof enrichSpawnEvent>[0]);

    const telegramResult = enrichSpawnEvent({
      event: "subagent_spawning",
      payload: {
        subagent_type: "oe-orchestrator",
        task_description: "Resume shared task payload",
      },
      context: {
        session_id: "sess_same_lineage",
        parent_session: "sess_same_lineage",
        project: "project-guardrail",
        ownership: {
          channel_type: "telegram",
          channel_conversation_id: "conv-telegram-009",
        },
      },
    } as Parameters<typeof enrichSpawnEvent>[0]);

    assert.notStrictEqual(
      feishuResult.enriched_payload.dedupe_key,
      telegramResult.enriched_payload.dedupe_key,
      "channel-distinct ownership must not collapse into the same dedupe key",
    );
  });
});

describe("Task 14: Cross-channel collision blocking after restart", () => {
  it("should return unsafe: true for cross-channel ambiguous restart", () => {
    // Simulate Feishu attempting to resume without valid ownership after restart
    const feishuResult = enrichSpawnEvent({
      event: "subagent_spawning",
      payload: {
        subagent_type: "oe-orchestrator",
        task_description: "Resume interrupted task",
      },
      context: {
        session_id: "sess-feishu-001",
        project: "default",
        restart_epoch: 1, // Restart happened
        // No ownership metadata - simulating the bug scenario
      },
    } as Parameters<typeof enrichSpawnEvent>[0]);

    // Should be marked as unsafe due to missing ownership after restart
    assert.strictEqual(
      (feishuResult as { unsafe?: boolean }).unsafe,
      true,
      "Feishu without valid ownership after restart should be marked unsafe"
    );
    assert.strictEqual(
      (feishuResult.enriched_payload as { ownership_status?: string }).ownership_status,
      "unsafe_ambiguous_restart",
      "Should have unsafe_ambiguous_restart status"
    );

    // Simulate Telegram also attempting to resume the same lineage
    const telegramResult = enrichSpawnEvent({
      event: "subagent_spawning",
      payload: {
        subagent_type: "oe-orchestrator",
        task_description: "Resume interrupted task",
      },
      context: {
        session_id: "sess-telegram-001",
        project: "default",
        restart_epoch: 1, // Same restart epoch
        // No ownership metadata
      },
    } as Parameters<typeof enrichSpawnEvent>[0]);

    // Should also be marked as unsafe
    assert.strictEqual(
      (telegramResult as { unsafe?: boolean }).unsafe,
      true,
      "Telegram without valid ownership after restart should be marked unsafe"
    );
    assert.strictEqual(
      (telegramResult.enriched_payload as { ownership_status?: string }).ownership_status,
      "unsafe_ambiguous_restart",
      "Should have unsafe_ambiguous_restart status"
    );
  });

  it("should NOT mark unsafe for valid same-channel ownership with matching epoch", () => {
    // Simulate Slack channel with valid ownership after revalidation
    const slackResult = enrichSpawnEvent({
      event: "subagent_spawning",
      payload: {
        subagent_type: "oe-orchestrator",
        task_description: "Resume interrupted task",
      },
      context: {
        session_id: "sess-slack-resumed",
        project: "default",
        restart_epoch: 1, // Restart happened
        ownership: {
          channel_type: "slack",
          channel_conversation_id: "conv-slack-123",
        },
      },
    } as Parameters<typeof enrichSpawnEvent>[0]);

    // Should NOT be marked unsafe - valid ownership present
    assert.strictEqual(
      (slackResult as { unsafe?: boolean }).unsafe,
      undefined,
      "Valid same-channel ownership should not be marked unsafe"
    );
    assert.strictEqual(
      slackResult.enriched_payload.ownership_status,
      "verified",
      "Should have verified ownership status"
    );
    
    // Should have channel-specific dedupe key
    assert.ok(
      slackResult.enriched_payload.dedupe_key.includes("slack"),
      "Dedupe key should include channel type for channel-aware deduplication"
    );
  });

  it("should mark unsafe when ownership metadata is missing", () => {
    const result = enrichSpawnEvent({
      event: "subagent_spawning",
      payload: {
        subagent_type: "oe-orchestrator",
        task_description: "Spawn after restart",
      },
      context: {
        session_id: "sess-001",
        project: "default",
        restart_epoch: 5, // Any restart epoch present
        // ownership completely missing
      },
    } as Parameters<typeof enrichSpawnEvent>[0]);

    assert.strictEqual(
      (result as { unsafe?: boolean }).unsafe,
      true,
      "Missing ownership with restart_epoch present should be unsafe"
    );
    assert.strictEqual(
      (result.enriched_payload as { ownership_status?: string }).ownership_status,
      "unsafe_ambiguous_restart",
      "Should indicate unsafe ambiguous restart"
    );
  });

  it("should allow fresh session without ownership when no restart_epoch", () => {
    const result = enrichSpawnEvent({
      event: "subagent_spawning",
      payload: {
        subagent_type: "oe-orchestrator",
        task_description: "Fresh task",
      },
      context: {
        session_id: "sess-fresh",
        project: "default",
        // No restart_epoch - this is a fresh session, not a restart
        // No ownership - acceptable for fresh sessions
      },
    } as Parameters<typeof enrichSpawnEvent>[0]);

    assert.strictEqual(
      (result as { unsafe?: boolean }).unsafe,
      undefined,
      "Fresh session without restart_epoch should not be marked unsafe"
    );
    assert.strictEqual(
      result.enriched_payload.ownership_status,
      "unverified",
      "Fresh session should have unverified status"
    );
  });
});
