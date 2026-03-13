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
  type RuntimeBridgeConfig,
} from "./runtime-bridge.js";

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
});
