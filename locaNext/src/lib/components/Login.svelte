<script>
  import {
    Form,
    TextInput,
    PasswordInput,
    Button,
    Checkbox,
    InlineNotification,
    InlineLoading
  } from "carbon-components-svelte";
  import { Login as LoginIcon } from "carbon-icons-svelte";
  import { onMount } from "svelte";
  import { api } from "$lib/api/client.js";
  import { isAuthenticated, user } from "$lib/stores/app.js";
  import { logger } from "$lib/utils/logger.js";

  // Form state
  let username = "";
  let password = "";
  let rememberMe = false;
  let isLoading = false;
  let error = "";

  // Remember me storage keys
  const REMEMBER_KEY = 'locanext_remember';
  const CREDENTIALS_KEY = 'locanext_creds';

  /**
   * Simple XOR encryption for credentials (basic obfuscation)
   * Note: This is NOT secure encryption, just basic obfuscation
   * For production, use proper encryption libraries
   */
  function encodeCredentials(username, password) {
    const data = JSON.stringify({ username, password });
    return btoa(data); // Base64 encode
  }

  function decodeCredentials(encoded) {
    try {
      const data = atob(encoded); // Base64 decode
      return JSON.parse(data);
    } catch {
      return null;
    }
  }

  /**
   * Save credentials to localStorage
   */
  function saveCredentials(username, password) {
    if (typeof window === 'undefined') return;

    logger.info("Saving credentials (remember me)", { username: username });
    localStorage.setItem(REMEMBER_KEY, 'true');
    const encoded = encodeCredentials(username, password);
    localStorage.setItem(CREDENTIALS_KEY, encoded);
  }

  /**
   * Load saved credentials
   */
  function loadCredentials() {
    if (typeof window === 'undefined') return null;

    const remember = localStorage.getItem(REMEMBER_KEY);
    if (remember !== 'true') return null;

    const encoded = localStorage.getItem(CREDENTIALS_KEY);
    if (!encoded) return null;

    return decodeCredentials(encoded);
  }

  /**
   * Clear saved credentials
   */
  function clearCredentials() {
    if (typeof window === 'undefined') return;

    logger.info("Clearing saved credentials");
    localStorage.removeItem(REMEMBER_KEY);
    localStorage.removeItem(CREDENTIALS_KEY);
  }

  /**
   * Handle login
   */
  async function handleLogin() {
    const startTime = performance.now();
    error = "";

    logger.userAction("Login attempted", { username: username, remember_me: rememberMe });

    if (!username || !password) {
      logger.warning("Login validation failed - missing credentials");
      error = "Please enter username and password";
      return;
    }

    isLoading = true;

    try {
      logger.apiCall("/api/login", "POST", { username: username });

      // Login via API
      await api.login(username, password);

      const elapsed = performance.now() - startTime;

      logger.success("Login successful", {
        username: username,
        remember_me: rememberMe,
        elapsed_ms: elapsed.toFixed(2)
      });

      // Save credentials if remember me is checked
      if (rememberMe) {
        saveCredentials(username, password);
      } else {
        clearCredentials();
      }

      // Success - user will be redirected by auth flow
    } catch (err) {
      const elapsed = performance.now() - startTime;

      logger.error("Login failed", {
        username: username,
        error: err.message,
        error_type: err.name,
        elapsed_ms: elapsed.toFixed(2)
      });

      error = err.message || "Login failed. Please check your credentials.";
    } finally {
      isLoading = false;
    }
  }

  /**
   * Try auto-login with saved credentials
   */
  async function tryAutoLogin() {
    const creds = loadCredentials();
    if (!creds) {
      logger.info("No saved credentials found - showing login form");
      return;
    }

    const startTime = performance.now();

    logger.info("Saved credentials found - attempting auto-login", {
      username: creds.username
    });

    username = creds.username;
    password = creds.password;
    rememberMe = true;

    // Auto-login
    isLoading = true;
    try {
      logger.apiCall("/api/login", "POST", { username: username, auto_login: true });
      await api.login(username, password);

      const elapsed = performance.now() - startTime;

      logger.success("Auto-login successful", {
        username: username,
        elapsed_ms: elapsed.toFixed(2)
      });

      // Success - user will be redirected
    } catch (err) {
      const elapsed = performance.now() - startTime;

      logger.error("Auto-login failed", {
        username: username,
        error: err.message,
        error_type: err.name,
        elapsed_ms: elapsed.toFixed(2)
      });

      // Clear invalid credentials
      clearCredentials();
      password = ""; // Clear password field
      error = "Auto-login failed. Please login again.";
    } finally {
      isLoading = false;
    }
  }

  onMount(() => {
    logger.component("Login", "mounted");
    // Try auto-login on mount
    tryAutoLogin();
  });

  function handleKeyPress(event) {
    if (event.key === 'Enter') {
      handleLogin();
    }
  }
</script>

<div class="login-container">
  <div class="login-box">
    <div class="login-header">
      <LoginIcon size={48} />
      <h1>LocaNext</h1>
      <p>Localization Tools Platform</p>
    </div>

    {#if error}
      <InlineNotification
        kind="error"
        title="Login Failed"
        subtitle={error}
        hideCloseButton={false}
        on:close={() => error = ""}
      />
    {/if}

    <form on:submit|preventDefault={handleLogin}>
      <TextInput
        labelText="Username"
        placeholder="Enter your username"
        bind:value={username}
        disabled={isLoading}
        on:keypress={handleKeyPress}
        required
      />

      <PasswordInput
        labelText="Password"
        placeholder="Enter your password"
        bind:value={password}
        disabled={isLoading}
        on:keypress={handleKeyPress}
        required
      />

      <Checkbox
        labelText="Remember me"
        bind:checked={rememberMe}
        disabled={isLoading}
      />

      <div class="login-actions">
        {#if isLoading}
          <InlineLoading description="Logging in..." />
        {:else}
          <Button type="submit" kind="primary" icon={LoginIcon}>
            Login
          </Button>
        {/if}
      </div>
    </form>

    <div class="login-footer">
      <p>Contact your administrator for access</p>
    </div>
  </div>
</div>

<style>
  .login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background: var(--cds-background);
    padding: 2rem;
  }

  .login-box {
    width: 100%;
    max-width: 400px;
    background: var(--cds-layer-01);
    padding: 3rem 2rem;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  .login-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .login-header :global(svg) {
    color: var(--cds-interactive-01);
    margin-bottom: 1rem;
  }

  .login-header h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    color: var(--cds-text-01);
  }

  .login-header p {
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  .login-actions {
    margin-top: 2rem;
    display: flex;
    justify-content: flex-end;
  }

  .login-footer {
    margin-top: 2rem;
    text-align: center;
    padding-top: 1.5rem;
    border-top: 1px solid var(--cds-border-subtle-01);
  }

  .login-footer p {
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  :global(.login-box .bx--form-item) {
    margin-bottom: 1.5rem;
  }

  :global(.login-box .bx--inline-notification) {
    margin-bottom: 1.5rem;
  }
</style>
