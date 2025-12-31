/**
 * SvelteKit Client Hooks
 * Handles file:// protocol routing for Electron app
 */

/**
 * Handle client-side routing for file:// protocol
 * When Electron loads file:///C:/path/to/app.asar/build/index.html,
 * the browser pathname is the full Windows path, which SvelteKit
 * tries to match as a route (and fails with "Not found").
 *
 * This hook intercepts navigation and normalizes the path to "/"
 * for the root page.
 */
export function handleError({ error, event, status, message }) {
  // Log errors but don't interfere
  console.error('[hooks.client] Error:', status, message, error);
  return {
    message: message || 'An error occurred'
  };
}

/**
 * Reroute function - intercept navigation before routing
 * This is called before each navigation to allow path transformation
 */
export function reroute({ url }) {
  // For file:// protocol, normalize the pathname
  if (url.protocol === 'file:') {
    // Check if the path looks like a Windows file path (contains drive letter)
    const pathname = url.pathname;
    if (pathname.match(/^\/[A-Z]:/i)) {
      // This is a Windows absolute path being interpreted as a route
      // Normalize to root
      console.log('[hooks.client] Normalizing file:// path to root:', pathname);
      return '/';
    }
  }
  // For other URLs, return the pathname as-is
  return url.pathname;
}
