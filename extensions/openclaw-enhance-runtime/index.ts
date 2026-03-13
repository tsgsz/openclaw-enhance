/**
 * OpenClaw Enhance Runtime Extension
 *
 * Thin plugin surface for namespaced runtime integration.
 * The native subagent announce chain remains the only worker communication path.
 */

export { RuntimeBridge, type RuntimeBridgeConfig } from "./src/runtime-bridge.js";
export { createRuntimeBridge } from "./src/runtime-bridge.js";

// Extension metadata
export const EXTENSION_NAME = "openclaw-enhance-runtime";
export const EXTENSION_VERSION = "0.1.0";
export const EXTENSION_NAMESPACE = "oe";

/**
 * Extension activation entry point.
 *
 * Called by OpenClaw when the extension is loaded.
 */
export function activate(): void {
  // Extension activation logic
  console.log(`[${EXTENSION_NAME}] Extension activated`);
}

/**
 * Extension deactivation entry point.
 *
 * Called by OpenClaw when the extension is unloaded.
 */
export function deactivate(): void {
  // Extension cleanup logic
  console.log(`[${EXTENSION_NAME}] Extension deactivated`);
}

// Default export for OpenClaw plugin system
export default {
  name: EXTENSION_NAME,
  version: EXTENSION_VERSION,
  namespace: EXTENSION_NAMESPACE,
  activate,
  deactivate,
};
