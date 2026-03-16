<script>
  /**
   * NodeDetailPanel.svelte - Phase 28: Node Detail Panel
   *
   * Displays all attributes of a selected tree node with editable text fields
   * for EDITABLE_ATTRS and optimistic save on blur. Shows children as clickable
   * navigation links at the bottom.
   *
   * Phase 28: Hierarchical Tree UI (Plan 02)
   */
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';

  const API_BASE = getApiBase();

  // Props (Svelte 5 Runes)
  let {
    node = null,
    filePath = '',
    onChildClick = () => {}
  } = $props();

  // State
  let editValues = $state({});
  let saving = $state(new Set());
  let saveErrors = $state({});

  // Phase 29: Entity detection state
  let detectedEntities = $state([]);
  let detecting = $state(false);

  // Type color accent mapping (matching EntityCard/CodexEntityDetail)
  const TYPE_COLORS = {
    CharacterInfo: '#ee5396',    // magenta
    ItemInfo: '#0072c3',         // cyan
    SkillInfo: '#a56eff',        // purple
    SkillTreeInfo: '#a56eff',    // purple
    SkillNode: '#a56eff',        // purple
    RegionInfo: '#24a148',       // green/teal
    SceneObjectData: '#24a148',  // green
    GimmickGroupInfo: '#ff832b', // orange
    GimmickInfo: '#ff832b',      // orange
    KnowledgeInfo: '#009d9a',    // teal
    QuestInfo: '#0f62fe',        // blue
    SealDataInfo: '#d4bbff',     // light purple
    FactionGroup: '#c9a227',     // gold
    NodeWaypointInfo: '#82cfff'  // light blue
  };

  /**
   * Sorted attributes: editable first, then alphabetical
   */
  let sortedAttributes = $derived.by(() => {
    if (!node?.attributes) return [];
    const entries = Object.entries(node.attributes);
    const editableSet = new Set(node.editable_attrs || []);

    return entries.sort((a, b) => {
      const aEditable = editableSet.has(a[0]);
      const bEditable = editableSet.has(b[0]);
      if (aEditable && !bEditable) return -1;
      if (!aEditable && bEditable) return 1;
      return a[0].localeCompare(b[0]);
    });
  });

  /**
   * Check if an attribute is editable
   */
  function isEditable(attrName) {
    return (node?.editable_attrs || []).includes(attrName);
  }

  /**
   * Get accent color for the node tag
   */
  let accentColor = $derived(TYPE_COLORS[node?.tag] || 'var(--cds-text-02)');

  /**
   * Sync editValues when node changes
   */
  $effect(() => {
    if (node) {
      const vals = {};
      for (const attr of (node.editable_attrs || [])) {
        vals[attr] = node.attributes?.[attr] || '';
      }
      editValues = vals;
      saveErrors = {};
    }
  });

  /**
   * Save attribute with optimistic UI (PUT /gamedata/save)
   */
  async function saveAttribute(attrName, newValue) {
    const oldValue = node.attributes[attrName];
    if (newValue === oldValue) return; // no change

    // Optimistic: update local edit state + node attributes
    editValues = { ...editValues, [attrName]: newValue };
    node.attributes[attrName] = newValue;
    saving = new Set([...saving, attrName]);

    // Clear previous error for this attribute
    const newErrors = { ...saveErrors };
    delete newErrors[attrName];
    saveErrors = newErrors;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/save`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          xml_path: filePath,
          entity_index: parseInt(node.node_id.split('_').filter(s => /^\d+$/.test(s))[0] ?? '0'),
          attr_name: attrName,
          new_value: newValue
        })
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        throw new Error(errData.detail || errData.message || `Save failed (HTTP ${response.status})`);
      }
      const data = await response.json();
      if (!data.success) throw new Error(data.message || 'Save failed');
      logger.success('Attribute saved', { attr: attrName, value: newValue });
    } catch (err) {
      // Revert on failure
      node.attributes[attrName] = oldValue;
      editValues = { ...editValues, [attrName]: oldValue };
      saveErrors = { ...saveErrors, [attrName]: err.message };
      logger.error('Attribute save failed', { attr: attrName, error: err.message });
    } finally {
      const newSaving = new Set(saving);
      newSaving.delete(attrName);
      saving = newSaving;
    }
  }

  /**
   * Handle blur on editable input
   */
  function handleBlur(attrName) {
    saveAttribute(attrName, editValues[attrName]);
  }

  /**
   * Handle Enter key on editable input (save + blur)
   */
  function handleKeydown(event, attrName) {
    if (event.key === 'Enter') {
      event.target.blur();
    }
  }

  // ========================================
  // Entity Detection (Phase 29: AC highlights)
  // ========================================

  /**
   * Detect entity names in node attribute values via Aho-Corasick API
   */
  async function detectEntities(nodeData) {
    if (!nodeData?.attributes) {
      detectedEntities = [];
      return;
    }
    const editableAttrs = nodeData.editable_attrs || [];
    const allAttrs = Object.keys(nodeData.attributes);
    const attrsToScan = allAttrs.filter(a => nodeData.attributes[a] && String(nodeData.attributes[a]).length > 0);

    if (attrsToScan.length === 0) {
      detectedEntities = [];
      return;
    }

    detecting = true;
    try {
      const allDetected = [];
      for (const attr of attrsToScan) {
        const text = String(nodeData.attributes[attr] || '');
        if (!text || text.length < 2) continue;
        const response = await fetch(`${API_BASE}/api/ldm/gamedata/index/detect`, {
          method: 'POST',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });
        if (response.ok) {
          const data = await response.json();
          for (const entity of (data.entities || [])) {
            allDetected.push({ ...entity, attribute: attr });
          }
        }
      }
      detectedEntities = allDetected;
    } catch (err) {
      logger.error('Entity detection failed', { error: err.message });
    } finally {
      detecting = false;
    }
  }

  // Trigger entity detection when node changes
  $effect(() => {
    if (node) {
      detectEntities(node);
    } else {
      detectedEntities = [];
    }
  });

  /**
   * Get entities detected in a specific attribute
   */
  function entitiesInAttr(attrName) {
    return detectedEntities.filter(e => e.attribute === attrName);
  }

  /**
   * Build highlighted text segments for an attribute value
   */
  function highlightText(text, entities, attrName) {
    const attrEntities = entities.filter(e => e.attribute === attrName);
    if (attrEntities.length === 0) return [{ text, isHighlight: false }];

    // Sort by start position, then by length descending (prefer longer matches)
    const sorted = [...attrEntities].sort((a, b) => a.start - b.start || b.end - a.end);

    const segments = [];
    let lastEnd = 0;

    for (const entity of sorted) {
      // Skip overlapping entities
      if (entity.start < lastEnd) continue;

      // Add non-highlighted text before this entity
      if (entity.start > lastEnd) {
        segments.push({ text: text.slice(lastEnd, entity.start), isHighlight: false });
      }

      // Add highlighted entity
      segments.push({
        text: text.slice(entity.start, entity.end),
        isHighlight: true,
        entity
      });

      lastEnd = entity.end;
    }

    // Add remaining text
    if (lastEnd < text.length) {
      segments.push({ text: text.slice(lastEnd), isHighlight: false });
    }

    return segments;
  }
</script>

{#if node}
  <div class="node-detail-panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="header-accent" style="background: {accentColor}"></div>
      <div class="header-content">
        <h3 class="node-tag-title">{node.tag}</h3>
        <span class="node-id">{node.node_id}</span>
      </div>
    </div>

    <!-- Attributes Section -->
    <div class="attributes-section">
      <h4 class="section-title">Attributes</h4>
      {#each sortedAttributes as [key, value] (key)}
        {#if isEditable(key)}
          <div class="attr-row editable">
            <div class="attr-key-row">
              <label class="attr-key" for="attr-{key}">{key}</label>
              {#if entitiesInAttr(key).length > 0}
                <span class="entity-badge" title="Contains {entitiesInAttr(key).length} entity reference(s)">
                  {entitiesInAttr(key).length}
                </span>
              {/if}
            </div>
            <div class="attr-input-wrapper">
              <input
                id="attr-{key}"
                class="attr-input"
                type="text"
                bind:value={editValues[key]}
                onblur={() => handleBlur(key)}
                onkeydown={(e) => handleKeydown(e, key)}
                disabled={saving.has(key)}
              />
              {#if saving.has(key)}
                <span class="saving-indicator" title="Saving..."></span>
              {/if}
            </div>
            {#if saveErrors[key]}
              <span class="save-error">{saveErrors[key]}</span>
            {/if}
          </div>
        {:else}
          <div class="attr-row">
            <span class="attr-key">{key}</span>
            <span class="attr-value" title={String(value ?? '')}>
              {#each highlightText(String(value ?? ''), detectedEntities, key) as segment}
                {#if segment.isHighlight}
                  <mark class="entity-highlight" title="{segment.entity.entity_name} ({segment.entity.tag})">{segment.text}</mark>
                {:else}
                  {segment.text}
                {/if}
              {/each}
            </span>
          </div>
        {/if}
      {/each}
    </div>

    <!-- Children Section -->
    {#if node.children?.length > 0}
      <div class="children-section">
        <h4 class="section-title">Children ({node.children.length})</h4>
        <div class="children-list">
          {#each node.children as child (child.node_id)}
            <button class="child-link" onclick={() => onChildClick(child)}>
              <span class="child-tag">{child.tag}</span>
              <span class="child-name">
                {child.attributes?.[child.editable_attrs?.[0]] || child.attributes?.Key || child.node_id}
              </span>
            </button>
          {/each}
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .node-detail-panel {
    display: flex;
    flex-direction: column;
    gap: 0;
    height: 100%;
    background: var(--cds-layer-01);
  }

  /* Header */
  .panel-header {
    display: flex;
    align-items: stretch;
    gap: 0;
    padding: 0;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .header-accent {
    width: 4px;
    flex-shrink: 0;
  }

  .header-content {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    padding: 0.75rem;
  }

  .node-tag-title {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .node-id {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    font-family: 'IBM Plex Mono', monospace;
  }

  /* Section Titles */
  .section-title {
    margin: 0 0 0.5rem;
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  /* Attributes */
  .attributes-section {
    padding: 0.75rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    overflow-y: auto;
    flex: 1;
    min-height: 0;
  }

  .attr-row {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .attr-row.editable {
    gap: 0.25rem;
  }

  .attr-key {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .attr-row.editable .attr-key {
    color: var(--cds-link-01);
  }

  .attr-value {
    font-size: 0.875rem;
    color: var(--cds-text-01);
    word-break: break-word;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
  }

  .attr-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .attr-input {
    width: 100%;
    padding: 0.375rem 0.5rem;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    font-family: 'IBM Plex Mono', monospace;
    outline: none;
    transition: border-color var(--transition-fast, 0.15s ease), background var(--transition-fast, 0.15s ease);
  }

  .attr-input:focus {
    border-color: var(--cds-focus);
    box-shadow: 0 0 0 1px var(--cds-focus);
  }

  .attr-input:disabled {
    opacity: 0.6;
  }

  .saving-indicator {
    position: absolute;
    right: 0.5rem;
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 50%;
    background: var(--cds-link-01);
    animation: pulse-save 1s ease-in-out infinite;
  }

  @keyframes pulse-save {
    0%, 100% { opacity: 0.3; transform: scale(0.8); }
    50% { opacity: 1; transform: scale(1); }
  }

  .save-error {
    font-size: 0.6875rem;
    color: var(--cds-support-error);
  }

  /* Children */
  .children-section {
    padding: 0.75rem;
    flex-shrink: 0;
    max-height: 200px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--cds-border-subtle-01) transparent;
  }

  .children-list {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .child-link {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.375rem 0.5rem;
    background: transparent;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    font-size: 0.75rem;
    color: var(--cds-text-01);
    transition: background var(--transition-fast, 0.1s ease), border-color var(--transition-fast, 0.1s ease);
  }

  .child-link:hover {
    background: var(--cds-layer-hover-01);
    border-color: var(--cds-border-strong-01);
  }

  .child-link:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .child-tag {
    font-weight: 500;
    color: var(--cds-text-02);
    flex-shrink: 0;
    font-size: 0.6875rem;
  }

  .child-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--cds-text-01);
  }

  /* Phase 29: Entity detection highlights */
  .attr-key-row {
    display: flex;
    align-items: center;
    gap: 0.375rem;
  }

  .entity-highlight {
    background-color: var(--cds-highlight, rgba(255, 214, 0, 0.25));
    border-radius: 2px;
    padding: 0 0.125rem;
    cursor: help;
    border-bottom: 1px dashed var(--cds-border-interactive, var(--cds-interactive));
  }

  .entity-badge {
    font-size: 0.625rem;
    font-weight: 600;
    padding: 1px 5px;
    border-radius: 8px;
    background: var(--cds-support-info, #0043ce);
    color: var(--cds-inverse-01, #fff);
    flex-shrink: 0;
    line-height: 1.2;
  }
</style>
