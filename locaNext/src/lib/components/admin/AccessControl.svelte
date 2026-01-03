<script>
  /**
   * AccessControl.svelte - DESIGN-001
   *
   * Admin panel for managing access to restricted resources.
   * Features:
   * - Toggle restriction on/off
   * - View users with access
   * - Add/remove user access
   */
  import { createEventDispatcher, onMount } from 'svelte';
  import { Modal, Toggle, Button, InlineLoading, Tag } from 'carbon-components-svelte';
  import { Add, TrashCan, Locked, Unlocked, User, Close } from 'carbon-icons-svelte';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { logger } from '$lib/utils/logger.js';

  const dispatch = createEventDispatcher();
  const API_BASE = getApiBase();

  // Props
  let {
    open = $bindable(false),
    resourceType = 'platform',  // 'platform' or 'project'
    resourceId = null,
    resourceName = ''
  } = $props();

  // State
  let isRestricted = $state(false);
  let accessList = $state([]);
  let allUsers = $state([]);
  let loading = $state(false);
  let saving = $state(false);
  let showUserPicker = $state(false);
  let selectedUserId = $state(null);

  // Fetch resource status and access list
  async function loadData() {
    if (!resourceId) return;
    loading = true;

    try {
      // Fetch resource to get is_restricted
      const resourceRes = await fetch(
        `${API_BASE}/api/ldm/${resourceType}s/${resourceId}`,
        { headers: getAuthHeaders() }
      );
      if (resourceRes.ok) {
        const data = await resourceRes.json();
        isRestricted = data.is_restricted || false;
      }

      // Fetch access list
      const accessRes = await fetch(
        `${API_BASE}/api/ldm/${resourceType}s/${resourceId}/access`,
        { headers: getAuthHeaders() }
      );
      if (accessRes.ok) {
        accessList = await accessRes.json();
      }

      // Fetch all users for picker
      const usersRes = await fetch(`${API_BASE}/api/admin/users`, {
        headers: getAuthHeaders()
      });
      if (usersRes.ok) {
        allUsers = await usersRes.json();
      }
    } catch (err) {
      logger.error('Failed to load access data', { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Toggle restriction
  async function toggleRestriction() {
    saving = true;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/${resourceType}s/${resourceId}/restriction?is_restricted=${!isRestricted}`,
        { method: 'PUT', headers: getAuthHeaders() }
      );
      if (response.ok) {
        isRestricted = !isRestricted;
        logger.success(`${resourceType} ${isRestricted ? 'restricted' : 'made public'}`);
        dispatch('change', { isRestricted });
      } else {
        const error = await response.json();
        logger.error('Failed to update restriction', { error: error.detail });
      }
    } catch (err) {
      logger.error('Error updating restriction', { error: err.message });
    } finally {
      saving = false;
    }
  }

  // Grant access to user
  async function grantAccess(userId) {
    saving = true;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/${resourceType}s/${resourceId}/access`,
        {
          method: 'POST',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_ids: [userId] })
        }
      );
      if (response.ok) {
        logger.success('Access granted');
        await loadData();  // Refresh list
        showUserPicker = false;
        selectedUserId = null;
      } else {
        const error = await response.json();
        logger.error('Failed to grant access', { error: error.detail });
      }
    } catch (err) {
      logger.error('Error granting access', { error: err.message });
    } finally {
      saving = false;
    }
  }

  // Revoke access from user
  async function revokeAccess(userId) {
    saving = true;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/${resourceType}s/${resourceId}/access/${userId}`,
        { method: 'DELETE', headers: getAuthHeaders() }
      );
      if (response.ok) {
        logger.success('Access revoked');
        await loadData();  // Refresh list
      } else {
        const error = await response.json();
        logger.error('Failed to revoke access', { error: error.detail });
      }
    } catch (err) {
      logger.error('Error revoking access', { error: err.message });
    } finally {
      saving = false;
    }
  }

  // Users not in access list
  let availableUsers = $derived(
    allUsers.filter(u => !accessList.some(a => a.user_id === u.id))
  );

  // Load data when modal opens
  $effect(() => {
    if (open && resourceId) {
      loadData();
    }
  });

  function handleClose() {
    open = false;
    dispatch('close');
  }
</script>

<Modal
  bind:open
  modalHeading="Manage Access: {resourceName}"
  passiveModal
  size="sm"
  on:close={handleClose}
>
  {#if loading}
    <div class="loading-state">
      <InlineLoading description="Loading access settings..." />
    </div>
  {:else}
    <div class="access-control">
      <!-- Restriction Toggle -->
      <div class="restriction-section">
        <div class="restriction-header">
          <div class="restriction-label">
            {#if isRestricted}
              <Locked size={20} />
              <span>Restricted</span>
            {:else}
              <Unlocked size={20} />
              <span>Public</span>
            {/if}
          </div>
          <Toggle
            size="sm"
            toggled={isRestricted}
            disabled={saving}
            on:toggle={toggleRestriction}
          />
        </div>
        <p class="restriction-help">
          {#if isRestricted}
            Only users with explicit access can see this {resourceType}.
          {:else}
            All users can see this {resourceType}.
          {/if}
        </p>
      </div>

      <!-- Access List (only shown when restricted) -->
      {#if isRestricted}
        <div class="access-section">
          <div class="access-header">
            <h4>Users with Access</h4>
            <Button
              kind="ghost"
              size="small"
              icon={Add}
              iconDescription="Add user"
              disabled={saving || availableUsers.length === 0}
              on:click={() => showUserPicker = true}
            >
              Add User
            </Button>
          </div>

          {#if accessList.length === 0}
            <p class="empty-state">No users have been granted access yet.</p>
          {:else}
            <ul class="access-list">
              {#each accessList as user}
                <li class="access-item">
                  <div class="user-info">
                    <User size={16} />
                    <span class="username">{user.username}</span>
                    {#if user.full_name}
                      <span class="full-name">({user.full_name})</span>
                    {/if}
                  </div>
                  <Button
                    kind="danger-ghost"
                    size="small"
                    icon={TrashCan}
                    iconDescription="Revoke access"
                    disabled={saving}
                    on:click={() => revokeAccess(user.user_id)}
                  />
                </li>
              {/each}
            </ul>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</Modal>

<!-- User Picker Modal -->
<Modal
  bind:open={showUserPicker}
  modalHeading="Add User"
  primaryButtonText="Grant Access"
  primaryButtonDisabled={!selectedUserId || saving}
  secondaryButtonText="Cancel"
  size="xs"
  on:click:button--primary={() => grantAccess(selectedUserId)}
  on:click:button--secondary={() => { showUserPicker = false; selectedUserId = null; }}
>
  {#if availableUsers.length === 0}
    <p>All users already have access.</p>
  {:else}
    <div class="user-picker">
      {#each availableUsers as user}
        <button
          class="user-option"
          class:selected={selectedUserId === user.id}
          onclick={() => selectedUserId = user.id}
        >
          <User size={16} />
          <span class="username">{user.username}</span>
          {#if user.full_name}
            <span class="full-name">{user.full_name}</span>
          {/if}
        </button>
      {/each}
    </div>
  {/if}
</Modal>

<style>
  .loading-state {
    display: flex;
    justify-content: center;
    padding: 2rem;
  }

  .access-control {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .restriction-section {
    padding: 1rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
  }

  .restriction-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
  }

  .restriction-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 500;
    color: var(--cds-text-01);
  }

  .restriction-help {
    font-size: 0.875rem;
    color: var(--cds-text-02);
    margin: 0;
  }

  .access-section {
    border-top: 1px solid var(--cds-border-subtle-01);
    padding-top: 1rem;
  }

  .access-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
  }

  .access-header h4 {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .empty-state {
    color: var(--cds-text-02);
    font-size: 0.875rem;
    text-align: center;
    padding: 1rem;
  }

  .access-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .access-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    transition: background 0.15s ease;
  }

  .access-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .user-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .username {
    font-weight: 500;
    color: var(--cds-text-01);
  }

  .full-name {
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  /* User picker */
  .user-picker {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .user-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: transparent;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s ease;
  }

  .user-option:hover {
    background: var(--cds-layer-hover-01);
  }

  .user-option.selected {
    background: var(--cds-layer-selected-01);
    border-color: var(--cds-focus);
  }
</style>
