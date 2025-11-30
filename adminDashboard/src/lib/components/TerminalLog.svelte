<script>
  export let logs = [];
  export let title = 'System Logs';
  export let height = '500px';
  export let live = false;

  let terminalEl;
  let autoScroll = true;

  $: if (terminalEl && autoScroll && logs.length > 0) {
    setTimeout(() => {
      terminalEl.scrollTop = terminalEl.scrollHeight;
    }, 50);
  }

  function getLogClass(log) {
    if (log.status === 'error' || log.error_message) return 'log-error';
    if (log.status === 'success') return 'log-success';
    if (log.status === 'warning') return 'log-warning';
    return 'log-info';
  }

  function getLogIcon(log) {
    if (log.status === 'error' || log.error_message) return '✗';
    if (log.status === 'success') return '✓';
    if (log.status === 'warning') return '⚠';
    return '›';
  }

  function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
</script>

<div class="terminal-container">
  <div class="terminal-header">
    <div class="terminal-title">
      {#if live}
        <span class="live-indicator"></span>
      {/if}
      {title}
    </div>
    <div class="terminal-controls">
      <label class="auto-scroll-toggle">
        <input type="checkbox" bind:checked={autoScroll} />
        Auto-scroll
      </label>
    </div>
  </div>
  <div class="terminal-body" bind:this={terminalEl} style="height: {height};">
    {#if logs.length === 0}
      <div class="terminal-empty">
        <span class="blink">_</span> Waiting for activity...
      </div>
    {:else}
      {#each logs as log, i}
        <div class="terminal-line {getLogClass(log)}">
          <span class="log-timestamp">[{formatTimestamp(log.timestamp)}]</span>
          <span class="log-icon">{getLogIcon(log)}</span>
          <span class="log-app">{log.tool_name || 'SYSTEM'}</span>
          <span class="log-separator">→</span>
          <span class="log-function">{log.function_name || 'unknown'}</span>
          <span class="log-user">({log.username})</span>
          {#if log.duration_seconds}
            <span class="log-duration">{log.duration_seconds.toFixed(2)}s</span>
          {/if}
          {#if log.error_message}
            <div class="log-error-detail">
              └─ Error: {log.error_message}
            </div>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .terminal-container {
    background: #161616;
    border: 1px solid #393939;
    border-radius: 4px;
    font-family: 'Courier New', 'Consolas', monospace;
    overflow: hidden;
  }

  .terminal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #1a1a1a;
    border-bottom: 1px solid #393939;
    padding: 8px 16px;
  }

  .terminal-title {
    color: #42be65;
    font-size: 0.875rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .live-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: #24a148;
    border-radius: 50%;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .terminal-controls {
    display: flex;
    gap: 12px;
  }

  .auto-scroll-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    color: #c6c6c6;
    cursor: pointer;
  }

  .auto-scroll-toggle input[type="checkbox"] {
    cursor: pointer;
  }

  .terminal-body {
    background: #0f0f0f;
    color: #c6c6c6;
    padding: 12px;
    overflow-y: auto;
    font-size: 0.8125rem;
    line-height: 1.6;
  }

  .terminal-body::-webkit-scrollbar {
    width: 8px;
  }

  .terminal-body::-webkit-scrollbar-track {
    background: #161616;
  }

  .terminal-body::-webkit-scrollbar-thumb {
    background: #393939;
    border-radius: 4px;
  }

  .terminal-body::-webkit-scrollbar-thumb:hover {
    background: #525252;
  }

  .terminal-empty {
    color: #8d8d8d;
    text-align: center;
    padding: 40px 20px;
  }

  .blink {
    animation: blink 1s infinite;
  }

  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }

  .terminal-line {
    padding: 2px 0;
    display: flex;
    gap: 8px;
    align-items: baseline;
  }

  .log-timestamp {
    color: #8d8d8d;
    min-width: 75px;
  }

  .log-icon {
    min-width: 16px;
    font-weight: 700;
  }

  .log-app {
    color: #78a9ff;
    font-weight: 600;
    min-width: 100px;
  }

  .log-separator {
    color: #4589ff;
  }

  .log-function {
    color: #ffb000;
    font-weight: 500;
    min-width: 150px;
  }

  .log-user {
    color: #c6c6c6;
    font-size: 0.75rem;
  }

  .log-duration {
    color: #42be65;
    margin-left: auto;
    font-size: 0.75rem;
  }

  .log-error {
    background: rgba(218, 30, 40, 0.1);
  }

  .log-error .log-icon {
    color: #ff8389;
  }

  .log-success .log-icon {
    color: #42be65;
  }

  .log-warning .log-icon {
    color: #f1c21b;
  }

  .log-info .log-icon {
    color: #4589ff;
  }

  .log-error-detail {
    padding-left: 99px;
    color: #ff8389;
    font-size: 0.75rem;
    margin-top: 2px;
  }
</style>
