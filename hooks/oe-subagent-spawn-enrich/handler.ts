/**
 * Handler for oe-subagent-spawn-enrich hook.
 *
 * Enriches subagent_spawning events with:
 * - task_id: Unique identifier for this task
 * - project: Project context from runtime
 * - parent_session: Parent session ID
 * - eta_bucket: Categorized duration estimate
 * - dedupe_key: Deterministic key for duplicate detection
 */

import { createHash, randomBytes } from "crypto";

/** Input payload for spawn enrichment */
export interface SpawnEnrichInput {
  event: "subagent_spawning";
  payload: {
    subagent_type: string;
    task_description: string;
    estimated_toolcalls?: number;
    estimated_duration_minutes?: number;
  };
  context: {
    session_id: string;
    project?: string;
    parent_session?: string;
  };
}

/** Output with enriched spawn metadata */
export interface SpawnEnrichOutput {
  enriched_payload: {
    task_id: string;
    project: string;
    parent_session: string;
    eta_bucket: "short" | "medium" | "long";
    dedupe_key: string;
  };
}

/** ETA bucket categories */
type ETABucket = "short" | "medium" | "long";

/**
 * Generate a unique task ID.
 *
 * Format: task_{random}_{timestamp}
 */
function generateTaskId(): string {
  const random = randomBytes(4).toString("hex");
  const timestamp = Date.now().toString(36);
  return `task_${random}_${timestamp}`;
}

/**
 * Categorize duration into ETA bucket.
 *
 * @param minutes - Estimated duration in minutes
 * @returns ETA bucket category
 */
function categorizeETA(minutes: number | undefined): ETABucket {
  if (minutes === undefined || minutes < 0) {
    return "medium";
  }
  if (minutes < 5) {
    return "short";
  }
  if (minutes <= 30) {
    return "medium";
  }
  return "long";
}

/**
 * Generate a deterministic deduplication key.
 *
 * Format: {project}:{subagent_type}:{task_hash}:{date}
 *
 * @param project - Project identifier
 * @param subagentType - Type of subagent
 * @param taskDescription - Task description
 * @returns Dedupe key string
 */
function generateDedupeKey(
  project: string,
  subagentType: string,
  taskDescription: string,
): string {
  // Normalize task description for consistent hashing
  const normalized = taskDescription.toLowerCase().trim().replace(/\s+/g, " ");

  // Create task hash (first 8 chars of SHA256)
  const hash = createHash("sha256").update(normalized).digest("hex").slice(0, 8);

  // Get current date in YYYYMMDD format
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, "");

  return `${project}:${subagentType}:${hash}:${date}`;
}

/**
 * Enrich a subagent spawn event with additional metadata.
 *
 * @param input - Spawn event input with payload and context
 * @returns Enriched output with task metadata
 */
export function enrichSpawnEvent(
  input: SpawnEnrichInput,
): SpawnEnrichOutput {
  const { payload, context } = input;

  // Generate unique task ID
  const taskId = generateTaskId();

  // Extract or default project
  const project = context.project ?? "default";

  // Extract or derive parent session
  const parentSession = context.parent_session ?? context.session_id;

  // Categorize ETA from estimated duration or toolcalls
  let estimatedMinutes = payload.estimated_duration_minutes;
  if (estimatedMinutes === undefined && payload.estimated_toolcalls !== undefined) {
    // Rough heuristic: 3 minutes per toolcall
    estimatedMinutes = payload.estimated_toolcalls * 3;
  }
  const etaBucket = categorizeETA(estimatedMinutes);

  // Generate deduplication key
  const dedupeKey = generateDedupeKey(
    project,
    payload.subagent_type,
    payload.task_description,
  );

  return {
    enriched_payload: {
      task_id: taskId,
      project,
      parent_session: parentSession,
      eta_bucket: etaBucket,
      dedupe_key: dedupeKey,
    },
  };
}

/**
 * Main handler function for the hook.
 *
 * This is the entry point called by the OpenClaw hook system.
 *
 * @param input - Spawn event input
 * @returns Enriched output
 */
export function handler(input: SpawnEnrichInput): SpawnEnrichOutput {
  return enrichSpawnEvent(input);
}

// Default export for compatibility
export default handler;
