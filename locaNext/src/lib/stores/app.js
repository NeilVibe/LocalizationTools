import { writable } from 'svelte/store';

// Current selected app (xlstransfer, quicksearch, krsimilar, ldm)
// Default to LDM as main app
export const currentApp = writable('ldm');

// Current view (app or tasks)
export const currentView = writable('app');

// User authentication
export const user = writable(null);
export const isAuthenticated = writable(false);

// P9: Offline mode flag (set when "Start Offline" is clicked)
// When true, user works in local Offline Storage only
export const offlineMode = writable(false);

// Server connection
export const serverUrl = writable('http://localhost:8888');
export const isConnected = writable(false);
