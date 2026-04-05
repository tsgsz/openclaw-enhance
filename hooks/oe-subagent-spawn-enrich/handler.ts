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
import { readFileSync } from "fs";
import { homedir } from "os";
import { join } from "path";
import { sanitizeEnhanceOutwardText } from "../../extensions/openclaw-enhance-runtime/src/runtime-bridge.js";

/** Input payload for spawn enrichment */
export interface SpawnEnrichInput {
  event: "subagent_spawning";
  payload: {
    subagent_type: string;
    task_description: string;
    estimated_toolcalls?: number;
    estimated_duration_minutes?: number;
    prompt?: string;
  };
  context: {
    session_id: string;
    project?: string;
    parent_session?: string;
    current_model?: string;
    restart_epoch?: number;
    ownership?: {
      channel_type: string;
      channel_conversation_id: string;
    };
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
    project_context: ProjectContext;
    ownership_status?: string;
  };
  unsafe?: boolean;
  spawn_patch?: {
    agentId: string;
    runtime: "subagent";
    streamTo?: undefined;
  };
}

/** Project context resolved from registry and runtime state */
export interface ProjectContext {
  project_id: string;
  project_name: string;
  project_type: string;
  project_kind: string;
}

/** ETA bucket categories */
type ETABucket = "short" | "medium" | "long";

/** Default project context when no project is active or resolvable */
const DEFAULT_PROJECT_CONTEXT: ProjectContext = {
  project_id: "default",
  project_name: "default",
  project_type: "unknown",
  project_kind: "default",
};

/**
 * Safely read and parse a JSON file.
 * Returns null on any error (missing file, invalid JSON, permissions, etc.).
 */
function readJsonFile(filePath: string): Record<string, unknown> | null {
  try {
    const content = readFileSync(filePath, "utf-8");
    return JSON.parse(content) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * Get main agent's current model from openclaw.json
 */
function getMainAgentModel(): string | null {
  const openclawConfig = readJsonFile(join(homedir(), ".openclaw", "openclaw.json"));
  if (!openclawConfig) return null;
  
  const agents = openclawConfig.agents as { list?: unknown[] } | undefined;
  if (!agents?.list) return null;
  
  for (const agent of agents.list) {
    if (typeof agent === "object" && agent !== null) {
      const agentObj = agent as Record<string, unknown>;
      if (agentObj.id === "main" && typeof agentObj.model === "string") {
        return agentObj.model;
      }
    }
  }
  return null;
}

function managedRoot(): string {
  return join(homedir(), ".openclaw", "openclaw-enhance");
}

/**
 * Resolve project context from runtime state and registry files.
 *
 * Resolution chain:
 * 1. If context.project is explicitly set (non-empty, non-"default"): use it as-is
 * 2. Else if active_project in runtime-state.json exists: use it, look up registry for metadata
 * 3. Else: use "default"
 *
 * @param contextProject - The project field from the spawn event context
 * @returns Resolved project context with metadata
 */
function resolveProjectContext(contextProject: string | undefined): {
  projectId: string;
  projectContext: ProjectContext;
} {
  // 1. Explicit project (non-empty, non-default) — use as-is
  if (contextProject && contextProject !== "default") {
    const registry = readJsonFile(join(managedRoot(), "project-registry.json"));
    if (registry) {
      const projects = registry.projects as Record<string, Record<string, unknown>> | undefined;
      if (projects && projects[contextProject]) {
        const entry = projects[contextProject];
        return {
          projectId: contextProject,
          projectContext: {
            project_id: contextProject,
            project_name: (entry.name as string) || contextProject,
            project_type: (entry.type as string) || "unknown",
            project_kind: (entry.kind as string) || "unknown",
          },
        };
      }
    }
    return {
      projectId: contextProject,
      projectContext: {
        project_id: contextProject,
        project_name: contextProject,
        project_type: "unknown",
        project_kind: "unknown",
      },
    };
  }

  // 2. Check runtime state for active_project
  const runtimeState = readJsonFile(join(managedRoot(), "runtime-state.json"));
  if (runtimeState) {
    const activeProject = runtimeState.active_project as string | undefined;
    if (activeProject && activeProject !== "default") {
      const registry = readJsonFile(join(managedRoot(), "project-registry.json"));
      if (registry) {
        const projects = registry.projects as Record<string, Record<string, unknown>> | undefined;
        if (projects && projects[activeProject]) {
          const entry = projects[activeProject];
          return {
            projectId: activeProject,
            projectContext: {
              project_id: activeProject,
              project_name: (entry.name as string) || activeProject,
              project_type: (entry.type as string) || "unknown",
              project_kind: (entry.kind as string) || "unknown",
            },
          };
        }
      }
      return {
        projectId: activeProject,
        projectContext: {
          project_id: activeProject,
          project_name: activeProject,
          project_type: "unknown",
          project_kind: "unknown",
        },
      };
    }
  }

  // 3. Default fallback
  return {
    projectId: "default",
    projectContext: { ...DEFAULT_PROJECT_CONTEXT },
  };
}

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
 * With ownership: {project}:{subagent_type}:{channel_type}:{task_hash}:{date}
 *
 * @param project - Project identifier
 * @param subagentType - Type of subagent
 * @param taskDescription - Task description
 * @param ownership - Optional ownership metadata for channel-aware dedupe
 * @returns Dedupe key string
 */
function generateDedupeKey(
  project: string,
  subagentType: string,
  taskDescription: string,
  ownership?: { channel_type: string; channel_conversation_id: string },
): string {
  // Normalize task description for consistent hashing
  const normalized = taskDescription.toLowerCase().trim().replace(/\s+/g, " ");

  // Create task hash (first 8 chars of SHA256)
  const hash = createHash("sha256").update(normalized).digest("hex").slice(0, 8);

  // Get current date in YYYYMMDD format
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, "");

  // Include channel identity in dedupe key if ownership is present
  if (ownership?.channel_type) {
    return `${project}:${subagentType}:${ownership.channel_type}:${hash}:${date}`;
  }

  return `${project}:${subagentType}:${hash}:${date}`;
}

/**
 * Validate ownership metadata and detect ambiguous restart scenarios.
 *
 * @param context - The spawn event context
 * @returns Validation result with ownership status
 */
function validateOwnership(context: SpawnEnrichInput["context"]): {
  valid: boolean;
  unsafe: boolean;
  ownership_status?: string;
  ownership?: { channel_type: string; channel_conversation_id: string };
} {
  // If restart_epoch is present but ownership is missing/stale, this is unsafe
  if (context.restart_epoch !== undefined && !context.ownership) {
    return {
      valid: false,
      unsafe: true,
      ownership_status: "unsafe_ambiguous_restart",
    };
  }

  // Ownership is present and valid
  if (context.ownership?.channel_type && context.ownership?.channel_conversation_id) {
    return {
      valid: true,
      unsafe: false,
      ownership_status: "verified",
      ownership: context.ownership,
    };
  }

  // No ownership metadata, but no restart epoch - acceptable for fresh sessions
  return {
    valid: true,
    unsafe: false,
    ownership_status: "unverified",
  };
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

  // Validate ownership before processing
  const ownershipValidation = validateOwnership(context);
  if (ownershipValidation.unsafe) {
    return {
      unsafe: true,
      enriched_payload: {
        task_id: generateTaskId(),
        project: context.project || "default",
        parent_session: context.parent_session || context.session_id,
        eta_bucket: "medium",
        dedupe_key: generateDedupeKey(
          context.project || "default",
          payload.subagent_type,
          payload.task_description,
        ),
        project_context: DEFAULT_PROJECT_CONTEXT,
        ownership_status: ownershipValidation.ownership_status,
      },
    };
  }

  const requestedAgent = payload.subagent_type;
  const normalizedAgent =
    requestedAgent && requestedAgent !== "main" ? requestedAgent : "oe-orchestrator";

  const mutablePayload = payload as Record<string, unknown>;
  mutablePayload.subagent_type = normalizedAgent;
  mutablePayload.agentId = normalizedAgent;
  mutablePayload.runtime = "subagent";
  if ("streamTo" in mutablePayload) {
    delete mutablePayload.streamTo;
  }

  const parentSession = context.parent_session ?? context.session_id;
  const { projectId, projectContext } = resolveProjectContext(context.project);

  const projectNote = `[SYSTEM: project_path=${projectContext.project_id}]
[SYSTEM: project_type=${projectContext.project_type}]
[SYSTEM: project_kind=${projectContext.project_kind}]
[SYSTEM: Work in: ${projectContext.project_id}]
[SYSTEM: parent_session=${parentSession}]
`;

  if (normalizedAgent === "oe-orchestrator") {
    const mainModel = getMainAgentModel();
    const originalPrompt = payload.prompt || payload.task_description;
    const orchestratorNote = `[SYSTEM: Use model ${mainModel} for this task]
`;
    mutablePayload.prompt = sanitizeEnhanceOutwardText(orchestratorNote + projectNote + originalPrompt);
  } else {
    const originalPrompt = payload.prompt || payload.task_description;
    mutablePayload.prompt = sanitizeEnhanceOutwardText(projectNote + originalPrompt);
  }

  const taskId = generateTaskId();
  const project = projectId;

  // Categorize ETA from estimated duration or toolcalls
  let estimatedMinutes = payload.estimated_duration_minutes;
  if (estimatedMinutes === undefined && payload.estimated_toolcalls !== undefined) {
    // Rough heuristic: 3 minutes per toolcall
    estimatedMinutes = payload.estimated_toolcalls * 3;
  }
  const etaBucket = categorizeETA(estimatedMinutes);

  // Generate deduplication key with channel awareness
  const dedupeKey = generateDedupeKey(
    project,
    payload.subagent_type,
    payload.task_description,
    ownershipValidation.ownership,
  );

  return {
    enriched_payload: {
      task_id: taskId,
      project,
      parent_session: parentSession,
      eta_bucket: etaBucket,
      dedupe_key: dedupeKey,
      project_context: projectContext,
      ownership_status: ownershipValidation.ownership_status,
    },
    spawn_patch: {
      agentId: normalizedAgent,
      runtime: "subagent",
      streamTo: undefined,
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
