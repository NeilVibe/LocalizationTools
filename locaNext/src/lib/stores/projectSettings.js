/**
 * Per-Project Settings Store — Phase 56, Plan 02
 *
 * Stores LOC PATH and EXPORT PATH per project in localStorage,
 * keyed by project ID. Used by ProjectSettingsModal and merge services.
 */

import { browser } from '$app/environment';

const SETTINGS_PREFIX = 'locaNext_project_settings_';

const DEFAULT_SETTINGS = {
  locPath: '',
  exportPath: ''
};

/**
 * Get settings for a specific project.
 * Returns defaults if not found or on parse error.
 * @param {number|string} projectId
 * @returns {{ locPath: string, exportPath: string }}
 */
export function getProjectSettings(projectId) {
  if (!browser) return { ...DEFAULT_SETTINGS };

  try {
    const stored = localStorage.getItem(SETTINGS_PREFIX + projectId);
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
    }
  } catch (e) {
    // Corrupt JSON — return defaults
  }
  return { ...DEFAULT_SETTINGS };
}

/**
 * Save settings for a specific project.
 * @param {number|string} projectId
 * @param {{ locPath?: string, exportPath?: string }} settings
 */
export function setProjectSettings(projectId, settings) {
  if (!browser) return;
  localStorage.setItem(SETTINGS_PREFIX + projectId, JSON.stringify(settings));
}

/**
 * Remove settings for a specific project.
 * @param {number|string} projectId
 */
export function clearProjectSettings(projectId) {
  if (!browser) return;
  localStorage.removeItem(SETTINGS_PREFIX + projectId);
}
