/**
 * Preferences Store - User preferences including themes and display settings
 *
 * Persists to localStorage for cross-session persistence.
 */

import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';

// Default preferences
const defaultPreferences = {
  // Appearance
  theme: 'dark', // 'light' | 'dark'
  fontSize: 'medium', // 'small' | 'medium' | 'large'
  fontWeight: 'normal', // 'normal' | 'bold'

  // Grid columns (LDM)
  showIndex: false,
  showStringId: false,
  showReference: false,
  showTmResults: false,
  showQaResults: false,

  // TM Settings
  activeTmId: null,
  showTmSuggestions: true,

  // QA Settings
  enableLiveQa: false,
  enableSpellCheck: false,
  enableGrammarCheck: false,
  enableGlossaryCheck: false,
  enableInconsistencyCheck: false,

  // Reference Settings
  referenceMatchMode: 'stringIdOnly', // 'stringIdOnly' | 'stringIdAndSource'
  referenceFileId: null
};

// Load preferences from localStorage
function loadPreferences() {
  if (!browser) return defaultPreferences;

  try {
    const stored = localStorage.getItem('locaNext_preferences');
    if (stored) {
      const parsed = JSON.parse(stored);
      // Merge with defaults to ensure new settings are included
      return { ...defaultPreferences, ...parsed };
    }
  } catch (e) {
    console.error('Failed to load preferences:', e);
  }
  return defaultPreferences;
}

// Save preferences to localStorage
function savePreferences(prefs) {
  if (!browser) return;

  try {
    localStorage.setItem('locaNext_preferences', JSON.stringify(prefs));
  } catch (e) {
    console.error('Failed to save preferences:', e);
  }
}

// Create the preferences store
function createPreferencesStore() {
  const { subscribe, set, update } = writable(loadPreferences());

  // Auto-save on changes
  subscribe(prefs => {
    savePreferences(prefs);

    // Apply theme to document
    if (browser && prefs.theme) {
      document.documentElement.setAttribute('data-theme', prefs.theme);
    }
  });

  return {
    subscribe,
    set,
    update,

    // Theme actions
    setTheme: (theme) => {
      update(prefs => ({ ...prefs, theme }));
    },

    toggleTheme: () => {
      update(prefs => ({
        ...prefs,
        theme: prefs.theme === 'dark' ? 'light' : 'dark'
      }));
    },

    // Font actions
    setFontSize: (fontSize) => {
      update(prefs => ({ ...prefs, fontSize }));
    },

    setFontWeight: (fontWeight) => {
      update(prefs => ({ ...prefs, fontWeight }));
    },

    // Column toggles
    toggleColumn: (column) => {
      update(prefs => ({ ...prefs, [column]: !prefs[column] }));
    },

    setColumn: (column, visible) => {
      update(prefs => ({ ...prefs, [column]: visible }));
    },

    // TM settings
    setActiveTm: (tmId) => {
      update(prefs => ({ ...prefs, activeTmId: tmId }));
    },

    // QA settings
    setQaSetting: (setting, enabled) => {
      update(prefs => ({ ...prefs, [setting]: enabled }));
    },

    // Reference settings
    setReferenceMatchMode: (mode) => {
      update(prefs => ({ ...prefs, referenceMatchMode: mode }));
    },

    setReferenceFile: (fileId) => {
      update(prefs => ({ ...prefs, referenceFileId: fileId }));
    },

    // Reset to defaults
    reset: () => {
      set(defaultPreferences);
    }
  };
}

export const preferences = createPreferencesStore();

// Derived stores for specific preference groups
export const theme = derived(preferences, $prefs => $prefs.theme);
export const fontSize = derived(preferences, $prefs => $prefs.fontSize);
export const fontWeight = derived(preferences, $prefs => $prefs.fontWeight);

// Font size CSS values
export const fontSizeMap = {
  small: '12px',
  medium: '14px',
  large: '16px'
};

// Helper to get font size CSS
export function getFontSizeValue(size) {
  return fontSizeMap[size] || fontSizeMap.medium;
}

// Initialize theme on page load
if (browser) {
  // Apply saved theme immediately
  const prefs = loadPreferences();
  document.documentElement.setAttribute('data-theme', prefs.theme || 'dark');
}
