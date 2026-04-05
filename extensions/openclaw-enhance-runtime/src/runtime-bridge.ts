/**
 * Runtime Bridge for OpenClaw Enhance
 *
 * Provides minimal plugin surface for namespaced runtime integration.
 * Consumes enriched spawn events from the oe-subagent-spawn-enrich hook.
 *
 * Note: Native subagent announce chain remains the only worker communication path.
 * This bridge provides metadata enrichment and runtime state tracking only.
 */

/** Configuration for the runtime bridge */
export interface RuntimeBridgeConfig {
  /** Enable the bridge */
  enabled: boolean;
  /** Namespace for runtime integration */
  namespace: string;
  /** Logging level */
  logLevel: "debug" | "info" | "warn" | "error";
}

/** Enriched spawn event from the hook */
export interface EnrichedSpawnEvent {
  task_id: string;
  project: string;
  parent_session: string;
  eta_bucket: "short" | "medium" | "long";
  dedupe_key: string;
}

/** Spawn event payload */
export interface SpawnEventPayload {
  subagent_type: string;
  task_description: string;
  estimated_toolcalls?: number;
  estimated_duration_minutes?: number;
}

/** Full spawn event with context */
export interface SpawnEvent {
  event: "subagent_spawning";
  timestamp: string;
  payload: SpawnEventPayload & Partial<EnrichedSpawnEvent>;
  context: {
    session_id: string;
    project?: string;
  };
}

/** Runtime bridge instance */
export class RuntimeBridge {
  private config: RuntimeBridgeConfig;
  private activeTasks: Map<string, EnrichedSpawnEvent> = new Map();

  constructor(config: Partial<RuntimeBridgeConfig> = {}) {
    this.config = {
      enabled: config.enabled ?? true,
      namespace: config.namespace ?? "oe",
      logLevel: config.logLevel ?? "info",
    };
  }

  /**
   * Log a message at the configured level.
   */
  private log(
    level: RuntimeBridgeConfig["logLevel"],
    message: string,
  ): void {
    const levels: Record<string, number> = {
      debug: 0,
      info: 1,
      warn: 2,
      error: 3,
    };

    if (levels[level] >= levels[this.config.logLevel]) {
      console.log(`[${this.config.namespace}:runtime-bridge] [${level}] ${message}`);
    }
  }

  /**
   * Handle an enriched spawn event.
   *
   * @param event - The spawn event with enriched metadata
   * @returns True if the event was processed successfully
   */
  handleSpawnEvent(event: SpawnEvent): boolean {
    if (!this.config.enabled) {
      this.log("debug", "Bridge disabled, skipping spawn event");
      return false;
    }

    const enriched = event.payload as SpawnEventPayload & EnrichedSpawnEvent;

    // Validate enriched fields are present
    if (!enriched.task_id) {
      this.log("warn", "Spawn event missing task_id enrichment");
      return false;
    }

    // Track the active task
    this.activeTasks.set(enriched.task_id, {
      task_id: enriched.task_id,
      project: enriched.project ?? "default",
      parent_session: enriched.parent_session ?? event.context.session_id,
      eta_bucket: enriched.eta_bucket ?? "medium",
      dedupe_key: enriched.dedupe_key ?? "",
    });

    this.log(
      "info",
      `Tracked spawn: ${enriched.task_id} (${enriched.subagent_type}) ` +
        `[${enriched.eta_bucket}] project=${enriched.project}`,
    );

    return true;
  }

  /**
   * Get all active tasks.
   *
   * @returns Array of active task metadata
   */
  getActiveTasks(): EnrichedSpawnEvent[] {
    return Array.from(this.activeTasks.values());
  }

  /**
   * Get a specific task by ID.
   *
   * @param taskId - The task ID to look up
   * @returns Task metadata or undefined if not found
   */
  getTask(taskId: string): EnrichedSpawnEvent | undefined {
    return this.activeTasks.get(taskId);
  }

  /**
   * Mark a task as completed.
   *
   * @param taskId - The task ID to complete
   * @returns True if the task was found and removed
   */
  completeTask(taskId: string): boolean {
    const task = this.activeTasks.get(taskId);
    if (task) {
      this.activeTasks.delete(taskId);
      this.log("info", `Completed task: ${taskId}`);
      return true;
    }
    this.log("warn", `Attempted to complete unknown task: ${taskId}`);
    return false;
  }

  /**
   * Check if a task is a duplicate based on its dedupe key.
   *
   * @param dedupeKey - The deduplication key to check
   * @returns True if a task with this key is already active
   */
  isDuplicate(dedupeKey: string): boolean {
    for (const task of this.activeTasks.values()) {
      if (task.dedupe_key === dedupeKey) {
        return true;
      }
    }
    return false;
  }

  /**
   * Get the current configuration.
   */
  getConfig(): RuntimeBridgeConfig {
    return { ...this.config };
  }

  /**
   * Update the configuration.
   */
  updateConfig(config: Partial<RuntimeBridgeConfig>): void {
    this.config = { ...this.config, ...config };
    this.log("info", `Configuration updated: ${JSON.stringify(this.config)}`);
  }
}

/**
 * Create a new runtime bridge instance.
 *
 * @param config - Optional configuration overrides
 * @returns New RuntimeBridge instance
 */
export function createRuntimeBridge(
  config?: Partial<RuntimeBridgeConfig>,
): RuntimeBridge {
  return new RuntimeBridge(config);
}

/**
 * Known internal marker patterns that should be stripped from outward text.
 */
const INTERNAL_MARKERS = [
  /\[Pasted ~\d+ lines\]/g,
  /<\|tool_calls_section_begin\|>/g,
  /<\|tool_call_begin\|>/g,
  /<\|tool_call_end\|>/g,
  /<\|tool_calls_section_end\|>/g,
];

/**
 * Sanitize text for outward communication by stripping internal markers
 * and normalizing whitespace.
 *
 * @param value - The input text to sanitize
 * @returns Sanitized text with markers stripped and whitespace normalized
 */
export function sanitizeEnhanceOutwardText(value: string): string {
  let result = value;

  // Strip all known internal markers
  for (const marker of INTERNAL_MARKERS) {
    result = result.replace(marker, "");
  }

  // Collapse multiple whitespace into single space
  result = result.replace(/\s+/g, " ");

  // Strip leading and trailing whitespace
  result = result.trim();

  return result;
}
