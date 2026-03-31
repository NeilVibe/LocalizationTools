<script>
  /**
   * StatusColors.svelte -- Row status, QA flags, TM matches, reference data management.
   *
   * Phase 84 Batch 1: Extracted from VirtualGrid.svelte.
   * Renderless component (logic only, no markup). Parent delegates via bind:this.
   *
   * Writes to gridState: tmAppliedRows, referenceData, qaFlags, grid.rows (QA flag updates)
   * Reads from gridState: grid, getRowById, getRowIndexById
   */

  import {
    grid,
    getDisplayRows,
    tmAppliedRows,
    referenceData,
    qaFlags,
    rowHeightCache,
    getRowById,
    getRowIndexById,
  } from './gridState.svelte.ts';
  import { getStatusKind } from '$lib/utils/statusColors';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { preferences } from '$lib/stores/preferences.js';
  import { stripColorTags } from '$lib/utils/colorParser.js';

  // TMUI-01: Context panel threshold — lower than pretranslation to show more suggestions
  const CONTEXT_THRESHOLD = 0.62;

  // Props from parent (configuration only, per D-05)
  let {
    fileId = null,
    activeTMs = [],
  } = $props();

  // API base URL
  let API_BASE = $derived(getApiBase());

  // Module-local state
  let tmResults = $state(new Map()); // row_id -> { target, similarity, source }
  // FIX-04: tmSuggestions was dead internal state (written but never read externally).
  // RightPanel/TMTab has its own TM fetch via /api/ldm/tm/suggest.
  let tmLoading = $state(false);
  let qaLoading = $state(false);
  let lastQaResult = $state(null);
  let referenceLoading = $state(false);

  // TM cache clear when activeTMs changes
  let prevActiveTMId = $state(null);
  $effect(() => {
    const currentTMId = activeTMs?.[0]?.tm_id || null;
    if (currentTMId !== prevActiveTMId) {
      prevActiveTMId = currentTMId;
      tmResults = new Map();
    }
  });

  // ========================================
  // QA Functions
  // ========================================

  /** Update a row's QA flag count (exported for parent delegation) */
  export function updateRowQAFlag(rowId, flagCount) {
    const rowIndex = getRowIndexById(rowId);
    if (rowIndex !== undefined && getDisplayRows()[rowIndex]) {
      getDisplayRows()[rowIndex] = {
        ...getDisplayRows()[rowIndex],
        qa_flag_count: flagCount
      };
      grid.rowsVersion++;
      logger.info('Updated row QA flag', { rowId, flagCount });
    } else {
      logger.warning("Row not found for QA flag update", { rowId });
    }
  }

  /** Handle QA dismiss from inline badge (optimistic UI) */
  export function handleQADismiss(rowId) {
    const rowIndex = getRowIndexById(rowId);
    if (rowIndex !== undefined && getDisplayRows()[rowIndex]) {
      const currentCount = getDisplayRows()[rowIndex].qa_flag_count || 0;
      getDisplayRows()[rowIndex] = {
        ...getDisplayRows()[rowIndex],
        qa_flag_count: Math.max(0, currentCount - 1)
      };
      grid.rowsVersion++;
      logger.info('QA inline dismiss', { rowId, newCount: getDisplayRows()[rowIndex].qa_flag_count });
    }
  }

  /** Run QA check on a row */
  export async function runQACheck(rowId) {
    if (!rowId) return null;

    qaLoading = true;
    lastQaResult = null;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${rowId}/check-qa`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          checks: ["line", "pattern", "term"],
          force: true
        })
      });

      if (response.ok) {
        const result = await response.json();
        lastQaResult = result;

        const rowIndex = getRowIndexById(rowId);
        if (rowIndex !== undefined && getDisplayRows()[rowIndex]) {
          getDisplayRows()[rowIndex] = {
            ...getDisplayRows()[rowIndex],
            qa_flag_count: result.issue_count,
            qa_checked_at: result.checked_at
          };
          grid.rowsVersion++;
        }

        if (result.issue_count > 0) {
          logger.warning("QA issues found", { rowId, count: result.issue_count });
        } else {
          logger.success("QA check passed", { rowId });
        }

        return result;
      }
    } catch (err) {
      logger.error("QA check failed", { rowId, error: err.message });
    } finally {
      qaLoading = false;
    }

    return null;
  }

  /** Fetch QA results for a row */
  export async function fetchQAResults(rowId) {
    if (!rowId) return [];

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${rowId}/qa-results`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        return data.issues || [];
      }
    } catch (err) {
      logger.error("Failed to fetch QA results", { rowId, error: err.message });
    }

    return [];
  }

  // ========================================
  // TM Functions
  // ========================================

  /** Mark a row as TM-applied */
  export function markRowAsTMApplied(rowId, matchType = 'fuzzy') {
    tmAppliedRows.set(rowId.toString(), { match_type: matchType });
    logger.info("Row marked as TM-applied", { rowId, matchType });
  }

  /** Fetch TM suggestions for a source text — SKIP when no TM is active */
  export async function fetchTMSuggestions(sourceText, rowId) {
    if (!sourceText || !sourceText.trim()) {
      return;
    }
    // No active TMs → no point calling the API (it returns 0 matches from project rows anyway)
    if (!activeTMs || activeTMs.length === 0) {
      return;
    }

    tmLoading = true;

    try {
      const params = new URLSearchParams({
        source: sourceText,
        threshold: CONTEXT_THRESHOLD.toString(),
        max_results: '5'
      });

      if (activeTMs && activeTMs.length > 0) {
        params.append('tm_id', activeTMs[0].tm_id.toString());
      }
      if (fileId) params.append('file_id', fileId.toString());
      if (rowId) params.append('exclude_row_id', rowId.toString());

      const response = await fetch(`${API_BASE}/api/ldm/tm/suggest?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        const suggestions = data.suggestions || [];
        const tmId = activeTMs?.[0]?.tm_id || 'project-rows';
        logger.info("TM suggestions fetched", { count: suggestions.length, tmId });
      }
    } catch (err) {
      logger.error("Failed to fetch TM suggestions", { error: err.message });
    } finally {
      tmLoading = false;
    }
  }

  /** Get best TM match for a row (cached) */
  export function getTMResultForRow(row) {
    if (!row.id) return null;
    return tmResults.get(row.id) || null;
  }

  /** Fetch TM result for a row and cache it */
  export async function fetchTMResultForRow(row) {
    if (!row.source) return;
    if (!activeTMs || activeTMs.length === 0) return;

    const rowId = row.id;
    if (tmResults.has(rowId)) return;

    const tmId = activeTMs[0].tm_id;

    try {
      const params = new URLSearchParams({
        source: row.source,
        threshold: CONTEXT_THRESHOLD.toString(),
        max_results: '1',
        tm_id: tmId.toString()
      });

      const response = await fetch(`${API_BASE}/api/ldm/tm/suggest?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        if (data.suggestions && data.suggestions.length > 0) {
          const best = data.suggestions[0];
          tmResults.set(rowId, {
            target: best.target,
            similarity: best.similarity,
            source: best.source
          });
        }
      }
    } catch (err) {
      logger.error("[TM-FETCH] Exception", { rowId, error: err.message });
    }
  }

  // ========================================
  // Reference Data Functions
  // ========================================

  /** Load reference file data for matching */
  export async function loadReferenceData(refFileId) {
    if (!refFileId) {
      referenceData.clear();
      return;
    }

    referenceLoading = true;
    logger.info("Loading reference file", { fileId: refFileId });

    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${refFileId}/rows?limit=10000`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        const refRows = data.rows || [];

        referenceData.clear();
        for (const row of refRows) {
          if (row.string_id) {
            referenceData.set(row.string_id, {
              target: row.target,
              source: row.source
            });
          }
        }

        logger.success("Reference data loaded", { entries: referenceData.size });
      } else {
        logger.error("Failed to load reference file", { status: response.status });
      }
    } catch (err) {
      logger.error("Error loading reference", { error: err.message });
    } finally {
      referenceLoading = false;
    }
  }

  /** Get reference translation for a row */
  export function getReferenceForRow(row, matchMode) {
    if (!row.string_id || referenceData.size === 0) return null;

    const ref = referenceData.get(row.string_id);
    if (!ref) return null;

    if (matchMode === 'stringIdAndSource') {
      if (ref.source !== row.source) return null;
    }

    return ref.target;
  }

  /** Reactive: load reference when preference changes */
  $effect(() => {
    if ($preferences.referenceFileId) {
      loadReferenceData($preferences.referenceFileId);
    } else {
      referenceData.clear();
    }
  });

  // Export state getters for parent (tmResults, referenceLoading, etc.)
  export function getTMResults() { return tmResults; }
  export function isReferenceLoading() { return referenceLoading; }
  export function isTMLoading() { return tmLoading; }
  export function isQALoading() { return qaLoading; }
  export function getLastQAResult() { return lastQaResult; }
</script>
