import { writable } from 'svelte/store';

// Current selected app (xlstransfer, tool2, etc.)
export const currentApp = writable('xlstransfer');

// Current view (app or tasks)
export const currentView = writable('app');

// User authentication
export const user = writable(null);
export const isAuthenticated = writable(false);

// Server connection
export const serverUrl = writable('http://localhost:8888');
export const isConnected = writable(false);
