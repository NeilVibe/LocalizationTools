<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import adminAPI from '$lib/api/client.js';
  import { logger } from '$lib/utils/logger.js';

  // SvelteKit auto-passes these props - declare to avoid warnings
  export const data = {};

  let users = [];
  let loading = true;

  onMount(async () => {
    const startTime = performance.now();
    logger.component('UsersPage', 'mounted');

    try {
      logger.apiCall('/api/users', 'GET');
      users = await adminAPI.getAllUsers();

      const elapsed = performance.now() - startTime;

      logger.success('Users loaded successfully', {
        user_count: users.length,
        elapsed_ms: elapsed.toFixed(2)
      });

      loading = false;
    } catch (error) {
      const elapsed = performance.now() - startTime;

      logger.error('Failed to load users', {
        error: error.message,
        error_type: error.name,
        elapsed_ms: elapsed.toFixed(2)
      });

      loading = false;
    }
  });

  function viewUserDetails(userId) {
    logger.userAction('View user details', { user_id: userId });
    goto(`/users/${userId}`);
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <h1 class="page-title">User Management</h1>
    <p class="page-subtitle">Manage system users and permissions</p>
  </div>

  {#if loading}
    <div class="loading-container">
      <p>Loading users...</p>
    </div>
  {:else if users.length > 0}
    <div class="data-table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Username</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {#each users as user}
            <tr on:click={() => viewUserDetails(user.user_id)}>
              <td>{user.user_id}</td>
              <td>{user.username}</td>
              <td>{user.email || 'N/A'}</td>
              <td>{user.role || 'user'}</td>
              <td>
                <span class="status-badge success">Active</span>
              </td>
              <td>{new Date(user.created_at).toLocaleDateString()}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <div class="empty-state">
      <h3>No users found</h3>
      <p>Users will appear here once created</p>
    </div>
  {/if}
</div>
