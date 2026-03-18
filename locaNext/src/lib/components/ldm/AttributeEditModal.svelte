<script>
  /**
   * AttributeEditModal.svelte — Beautiful attribute editor modal
   * Opens on double-click of XML attribute in GameDataTree.
   * One Dark Pro theme with warm glow accents.
   */
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';

  const API_BASE = getApiBase();

  let {
    open = $bindable(false),
    attrName = '',
    attrValue = '',
    filePath = '',
    entityIndex = 0,
    onSave = () => {},
    onCancel = () => {}
  } = $props();

  let editValue = $state('');
  let saving = $state(false);
  let error = $state('');
  let textareaEl = $state(null);

  // Sync value when modal opens
  $effect(() => {
    if (open) {
      editValue = attrValue;
      error = '';
      // Focus textarea after render
      setTimeout(() => textareaEl?.focus(), 50);
    }
  });

  async function save() {
    if (editValue === attrValue) { close(); return; }
    saving = true;
    error = '';

    try {
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/save`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          xml_path: filePath,
          entity_index: entityIndex,
          attr_name: attrName,
          new_value: editValue
        })
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        throw new Error(data.detail || 'Save failed');
      }

      const data = await response.json();
      if (!data.success) throw new Error(data.message || 'Save failed');

      onSave(attrName, editValue);
      close();
    } catch (err) {
      error = err.message;
    } finally {
      saving = false;
    }
  }

  function close() {
    open = false;
    onCancel();
  }

  function handleKeydown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
    } else if (event.key === 's' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      save();
    }
  }

  function handleBackdropClick(event) {
    if (event.target === event.currentTarget) close();
  }
</script>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="modal-backdrop" onclick={handleBackdropClick} onkeydown={handleKeydown}>
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">
          <span class="modal-attr-name">{attrName}</span>
          <span class="modal-hint">Ctrl+S to save · Esc to cancel</span>
        </div>
      </div>
      <div class="modal-body">
        <textarea
          class="modal-textarea"
          bind:this={textareaEl}
          bind:value={editValue}
          onkeydown={handleKeydown}
          disabled={saving}
          rows="6"
          spellcheck="false"
        ></textarea>
        {#if error}
          <div class="modal-error">{error}</div>
        {/if}
      </div>
      <div class="modal-footer">
        <button class="modal-btn cancel" onclick={close} disabled={saving}>Cancel</button>
        <button class="modal-btn save" onclick={save} disabled={saving}>
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.15s ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(16px) scale(0.97); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  .modal-card {
    width: min(480px, 90vw);
    background: #1e1e1e;
    border: 1px solid rgba(212, 154, 92, 0.25);
    border-radius: 12px;
    box-shadow:
      0 24px 64px rgba(0, 0, 0, 0.5),
      0 0 0 1px rgba(255, 255, 255, 0.03),
      0 0 40px rgba(212, 154, 92, 0.08);
    animation: slideUp 0.2s ease-out;
    overflow: hidden;
  }

  .modal-header {
    padding: 16px 20px 12px;
    border-bottom: 1px solid #3c3c3c;
    background: rgba(33, 37, 43, 0.8);
  }

  .modal-title {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
  }

  .modal-attr-name {
    font-size: 15px;
    font-weight: 600;
    color: #d49a5c;
    font-family: 'IBM Plex Mono', monospace;
  }

  .modal-hint {
    font-size: 11px;
    color: #6b7280;
  }

  .modal-body {
    padding: 16px 20px;
  }

  .modal-textarea {
    width: 100%;
    min-height: 120px;
    padding: 12px 14px;
    background: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 8px;
    color: #d4d4d4;
    font-size: 13px;
    font-family: 'D2Coding', 'Noto Sans Mono CJK KR', 'IBM Plex Mono', monospace;
    line-height: 1.6;
    resize: vertical;
    outline: none;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    box-sizing: border-box;
  }

  .modal-textarea:focus {
    border-color: #d49a5c;
    box-shadow: 0 0 0 2px rgba(212, 154, 92, 0.15), 0 0 12px rgba(212, 154, 92, 0.1);
  }

  .modal-textarea:disabled {
    opacity: 0.5;
  }

  .modal-error {
    margin-top: 8px;
    padding: 6px 10px;
    background: rgba(224, 108, 117, 0.1);
    border: 1px solid rgba(224, 108, 117, 0.3);
    border-radius: 6px;
    color: #e06c75;
    font-size: 12px;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 12px 20px 16px;
    border-top: 1px solid #3c3c3c;
  }

  .modal-btn {
    padding: 8px 20px;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .modal-btn.cancel {
    background: #3c3c3c;
    color: #abb2bf;
  }
  .modal-btn.cancel:hover { background: #4c4c4c; }

  .modal-btn.save {
    background: linear-gradient(135deg, #d49a5c, #e88a3a);
    color: #1e1e1e;
    font-weight: 600;
  }
  .modal-btn.save:hover {
    box-shadow: 0 0 16px rgba(212, 154, 92, 0.3);
    transform: translateY(-1px);
  }
  .modal-btn.save:active { transform: translateY(0); }
  .modal-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
