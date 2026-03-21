/**
 * AI Capability Store - Svelte 5 Runes store for AI engine availability.
 *
 * Phase 45: Exposes runtime AI engine detection to all UI components.
 * Fetches from /api/ldm/ai-capabilities and provides reactive state.
 *
 * Usage:
 *   import { aiCapabilities, refreshCapabilities, isAvailable } from '$lib/stores/aiCapabilityStore';
 *   if (isAvailable('embeddings')) { ... }
 */

export type AICapability = "available" | "unavailable" | "checking";

export interface AICapabilities {
	embeddings: AICapability;
	semantic_search: AICapability;
	ai_summary: AICapability;
	tts: AICapability;
	image_gen: AICapability;
	light_mode: boolean;
	last_check: number;
}

// Svelte 5 Runes: module-level $state
let aiCapabilities = $state<AICapabilities>({
	embeddings: "checking",
	semantic_search: "checking",
	ai_summary: "checking",
	tts: "checking",
	image_gen: "checking",
	light_mode: false,
	last_check: 0,
});

/**
 * Fetch AI capabilities from the backend and update reactive state.
 * On error, sets all engines to "unavailable" (graceful degradation).
 */
async function refreshCapabilities(): Promise<void> {
	try {
		const resp = await fetch("/api/ldm/ai-capabilities");
		if (!resp.ok) {
			throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
		}
		const data = await resp.json();

		// Update reactive state
		aiCapabilities.embeddings = data.capabilities?.embeddings ?? "unavailable";
		aiCapabilities.semantic_search = data.capabilities?.semantic_search ?? "unavailable";
		aiCapabilities.ai_summary = data.capabilities?.ai_summary ?? "unavailable";
		aiCapabilities.tts = data.capabilities?.tts ?? "unavailable";
		aiCapabilities.image_gen = data.capabilities?.image_gen ?? "unavailable";
		aiCapabilities.light_mode = data.light_mode ?? false;
		aiCapabilities.last_check = data.last_check ?? 0;
	} catch (err) {
		console.error("[AI-CAPS] Failed to fetch capabilities:", err);
		// Graceful degradation: mark all as unavailable
		aiCapabilities.embeddings = "unavailable";
		aiCapabilities.semantic_search = "unavailable";
		aiCapabilities.ai_summary = "unavailable";
		aiCapabilities.tts = "unavailable";
		aiCapabilities.image_gen = "unavailable";
		aiCapabilities.light_mode = false;
		aiCapabilities.last_check = 0;
	}
}

/**
 * Check if a specific AI engine is available.
 */
function isAvailable(engine: string): boolean {
	return (aiCapabilities as Record<string, unknown>)[engine] === "available";
}

// Auto-probe on module load (runs when first imported)
refreshCapabilities();

export { aiCapabilities, refreshCapabilities, isAvailable };
