<script>
  export let logs = [];
  export let title = 'System Logs';
  export let height = '500px';
  export let live = false;

  let terminalEl;
  let autoScroll = true;
  let expandedLogs = {};

  $: if (terminalEl && autoScroll && logs.length > 0) {
    setTimeout(() => {
      terminalEl.scrollTop = terminalEl.scrollHeight;
    }, 50);
  }

  function getLogClass(log) {
    if (log.status === 'error' || log.error_message || log.level === 'ERROR') return 'log-error';
    if (log.status === 'success' || log.level === 'SUCCESS') return 'log-success';
    if (log.status === 'warning' || log.level === 'WARNING') return 'log-warning';
    return 'log-info';
  }

  function getLogIcon(log) {
    if (log.status === 'error' || log.error_message || log.level === 'ERROR') return '✗';
    if (log.status === 'success' || log.level === 'SUCCESS') return '✓';
    if (log.status === 'warning' || log.level === 'WARNING') return '⚠';
    return '›';
  }

  function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function hasDetails(log) {
    return log.file_info || log.parameters || (log.message && log.tool_name !== 'SERVER');
  }

  function toggleExpand(index) {
    expandedLogs[index] = !expandedLogs[index];
    expandedLogs = { ...expandedLogs };
  }

  function formatFileInfo(fileInfo) {
    if (!fileInfo) return null;
    if (typeof fileInfo === 'string') {
      try {
        return JSON.parse(fileInfo);
      } catch {
        return { path: fileInfo };
      }
    }
    return fileInfo;
  }

  function formatParameters(params) {
    if (!params) return null;
    if (typeof params === 'string') {
      try {
        return JSON.parse(params);
      } catch {
        return { value: params };
      }
    }
    return params;
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
          <div class="log-main" on:click={() => hasDetails(log) && toggleExpand(i)} on:keydown={(e) => e.key === 'Enter' && hasDetails(log) && toggleExpand(i)} role={hasDetails(log) ? 'button' : 'listitem'} tabindex={hasDetails(log) ? 0 : -1} class:expandable={hasDetails(log)}>
            <span class="log-timestamp">[{formatTimestamp(log.timestamp)}]</span>
            <span class="log-icon">{getLogIcon(log)}</span>
            {#if log.level}
              <span class="log-level log-level-{log.level?.toLowerCase()}">{log.level}</span>
            {/if}
            <span class="log-app">{log.tool_name || 'SYSTEM'}</span>
            <span class="log-separator">→</span>
            <span class="log-function">{log.function_name || 'unknown'}</span>
            <span class="log-user">({log.username})</span>
            {#if log.duration_seconds}
              <span class="log-duration">{log.duration_seconds.toFixed(2)}s</span>
            {/if}
            {#if hasDetails(log)}
              <span class="expand-indicator">{expandedLogs[i] ? '▼' : '▶'}</span>
            {/if}
          </div>

          <!-- Message display (always shown for server logs) -->
          {#if log.message && log.tool_name === 'SERVER'}
            <div class="log-message">
              <span class="tree-char">│</span>
              <span class="message-text">{log.message}</span>
            </div>
          {/if}

          <!-- Error display -->
          {#if log.error_message}
            <div class="log-error-detail">
              <span class="tree-char">└─</span>
              <span class="error-label">Error:</span>
              <span class="error-text">{log.error_message}</span>
            </div>
          {/if}

          <!-- Expandable details tree -->
          {#if expandedLogs[i] && hasDetails(log)}
            <div class="log-details">
              {#if log.message && log.tool_name !== 'SERVER'}
                <div class="detail-line">
                  <span class="tree-char">├─</span>
                  <span class="detail-label">Message:</span>
                  <span class="detail-value">{log.message}</span>
                </div>
              {/if}
              {#if log.file_info}
                {@const fileInfo = formatFileInfo(log.file_info)}
                <div class="detail-line">
                  <span class="tree-char">├─</span>
                  <span class="detail-label">File:</span>
                </div>
                {#if fileInfo}
                  {#each Object.entries(fileInfo) as [key, value], idx}
                    <div class="detail-line detail-nested">
                      <span class="tree-char">{idx === Object.entries(fileInfo).length - 1 ? '│  └─' : '│  ├─'}</span>
                      <span class="detail-key">{key}:</span>
                      <span class="detail-value">{value}</span>
                    </div>
                  {/each}
                {/if}
              {/if}
              {#if log.parameters}
                {@const params = formatParameters(log.parameters)}
                <div class="detail-line">
                  <span class="tree-char">{log.session_id || log.machine_id ? '├─' : '└─'}</span>
                  <span class="detail-label">Parameters:</span>
                </div>
                {#if params}
                  {#each Object.entries(params) as [key, value], idx}
                    <div class="detail-line detail-nested">
                      <span class="tree-char">{idx === Object.entries(params).length - 1 ? '│  └─' : '│  ├─'}</span>
                      <span class="detail-key">{key}:</span>
                      <span class="detail-value">{typeof value === 'object' ? JSON.stringify(value) : value}</span>
                    </div>
                  {/each}
                {/if}
              {/if}
              {#if log.session_id}
                <div class="detail-line">
                  <span class="tree-char">{log.machine_id ? '├─' : '└─'}</span>
                  <span class="detail-label">Session:</span>
                  <span class="detail-value detail-id">{log.session_id}</span>
                </div>
              {/if}
              {#if log.machine_id}
                <div class="detail-line">
                  <span class="tree-char">└─</span>
                  <span class="detail-label">Machine:</span>
                  <span class="detail-value detail-id">{log.machine_id}</span>
                </div>
              {/if}
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
    padding: 4px 0;
    display: flex;
    flex-direction: column;
    border-bottom: 1px solid rgba(255,255,255,0.03);
  }

  .terminal-line:hover {
    background: rgba(255,255,255,0.02);
  }

  .log-main {
    display: flex;
    gap: 8px;
    align-items: baseline;
    padding: 2px 0;
  }

  .log-main.expandable {
    cursor: pointer;
  }

  .log-main.expandable:hover {
    background: rgba(69, 137, 255, 0.1);
    border-radius: 2px;
  }

  .log-timestamp {
    color: #8d8d8d;
    min-width: 75px;
  }

  .log-icon {
    min-width: 16px;
    font-weight: 700;
  }

  .log-level {
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    min-width: 50px;
    text-align: center;
  }

  .log-level-info { background: rgba(69, 137, 255, 0.2); color: #78a9ff; }
  .log-level-success { background: rgba(66, 190, 101, 0.2); color: #42be65; }
  .log-level-warning { background: rgba(241, 194, 27, 0.2); color: #f1c21b; }
  .log-level-error { background: rgba(255, 131, 137, 0.2); color: #ff8389; }
  .log-level-critical { background: rgba(218, 30, 40, 0.3); color: #fa4d56; }

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

  .expand-indicator {
    color: #6f6f6f;
    font-size: 0.7rem;
    margin-left: 8px;
  }

  .log-error {
    background: rgba(218, 30, 40, 0.08);
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

  /* Tree structure elements */
  .tree-char {
    color: #525252;
    font-family: monospace;
    min-width: 24px;
  }

  .log-message {
    padding-left: 99px;
    display: flex;
    gap: 8px;
    margin-top: 2px;
  }

  .message-text {
    color: #a8a8a8;
    font-size: 0.8rem;
    word-break: break-word;
  }

  .log-error-detail {
    padding-left: 99px;
    display: flex;
    gap: 8px;
    margin-top: 2px;
  }

  .error-label {
    color: #ff8389;
    font-weight: 600;
    font-size: 0.75rem;
  }

  .error-text {
    color: #ffb3b8;
    font-size: 0.75rem;
    word-break: break-word;
  }

  .log-details {
    padding-left: 99px;
    margin-top: 4px;
    padding-top: 4px;
    border-left: 2px solid #303030;
    margin-left: 103px;
    padding-left: 12px;
  }

  .detail-line {
    display: flex;
    gap: 8px;
    align-items: baseline;
    padding: 1px 0;
  }

  .detail-nested {
    padding-left: 16px;
  }

  .detail-label {
    color: #78a9ff;
    font-size: 0.75rem;
    font-weight: 500;
    min-width: 70px;
  }

  .detail-key {
    color: #a8a8a8;
    font-size: 0.7rem;
    min-width: 80px;
  }

  .detail-value {
    color: #c6c6c6;
    font-size: 0.75rem;
    word-break: break-all;
  }

  .detail-id {
    color: #6f6f6f;
    font-family: monospace;
    font-size: 0.7rem;
  }
</style>
