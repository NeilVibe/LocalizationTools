<script>
  import { onMount } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import { UserMultiple, Add, Edit, TrashCan, Password, Checkmark, Close, Renew, Search } from 'carbon-icons-svelte';

  export const data = {};

  let users = [];
  let loading = true;
  let error = null;
  let searchQuery = '';

  // Modal states
  let showCreateModal = false;
  let showEditModal = false;
  let showResetPasswordModal = false;
  let selectedUser = null;

  // Form data
  let createForm = {
    username: '',
    password: '',
    email: '',
    full_name: '',
    team: '',
    language: '',
    department: '',
    role: 'user',
    must_change_password: true
  };

  let editForm = {
    email: '',
    full_name: '',
    team: '',
    language: '',
    department: '',
    role: 'user',
    is_active: true
  };

  let resetPasswordForm = {
    new_password: '',
    must_change_password: true
  };

  let formError = null;
  let formSuccess = null;

  onMount(async () => {
    await loadUsers();
  });

  async function loadUsers() {
    try {
      loading = true;
      error = null;
      users = await adminAPI.getAllUsers();
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  $: filteredUsers = users.filter(user => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      user.username?.toLowerCase().includes(query) ||
      user.email?.toLowerCase().includes(query) ||
      user.full_name?.toLowerCase().includes(query) ||
      user.team?.toLowerCase().includes(query) ||
      user.department?.toLowerCase().includes(query)
    );
  });

  // Create User
  function openCreateModal() {
    createForm = {
      username: '',
      password: '',
      email: '',
      full_name: '',
      team: '',
      language: '',
      department: '',
      role: 'user',
      must_change_password: true
    };
    formError = null;
    showCreateModal = true;
  }

  async function createUser() {
    try {
      formError = null;
      await adminAPI.adminCreateUser(createForm);
      showCreateModal = false;
      formSuccess = 'User created successfully';
      await loadUsers();
      setTimeout(() => formSuccess = null, 3000);
    } catch (err) {
      formError = err.message;
    }
  }

  // Edit User
  function openEditModal(user) {
    selectedUser = user;
    editForm = {
      email: user.email || '',
      full_name: user.full_name || '',
      team: user.team || '',
      language: user.language || '',
      department: user.department || '',
      role: user.role || 'user',
      is_active: user.is_active
    };
    formError = null;
    showEditModal = true;
  }

  async function updateUser() {
    try {
      formError = null;
      await adminAPI.adminUpdateUser(selectedUser.user_id, editForm);
      showEditModal = false;
      formSuccess = 'User updated successfully';
      await loadUsers();
      setTimeout(() => formSuccess = null, 3000);
    } catch (err) {
      formError = err.message;
    }
  }

  // Reset Password
  function openResetPasswordModal(user) {
    selectedUser = user;
    resetPasswordForm = {
      new_password: '',
      must_change_password: true
    };
    formError = null;
    showResetPasswordModal = true;
  }

  async function resetPassword() {
    try {
      formError = null;
      await adminAPI.adminResetPassword(
        selectedUser.user_id,
        resetPasswordForm.new_password,
        resetPasswordForm.must_change_password
      );
      showResetPasswordModal = false;
      formSuccess = 'Password reset successfully';
      setTimeout(() => formSuccess = null, 3000);
    } catch (err) {
      formError = err.message;
    }
  }

  // Activate/Deactivate
  async function toggleUserStatus(user) {
    try {
      if (user.is_active) {
        await adminAPI.deactivateUser(user.user_id);
        formSuccess = `User ${user.username} deactivated`;
      } else {
        await adminAPI.activateUser(user.user_id);
        formSuccess = `User ${user.username} activated`;
      }
      await loadUsers();
      setTimeout(() => formSuccess = null, 3000);
    } catch (err) {
      formError = err.message;
      setTimeout(() => formError = null, 3000);
    }
  }

  // Delete (soft delete)
  async function deleteUser(user) {
    if (!confirm(`Are you sure you want to deactivate user "${user.username}"?`)) return;

    try {
      await adminAPI.adminDeleteUser(user.user_id);
      formSuccess = `User ${user.username} deactivated`;
      await loadUsers();
      setTimeout(() => formSuccess = null, 3000);
    } catch (err) {
      formError = err.message;
      setTimeout(() => formError = null, 3000);
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <div class="header-content">
      <h1 class="page-title">
        <UserMultiple size={24} />
        User Management
      </h1>
      <p class="page-subtitle">Manage user accounts and permissions</p>
    </div>
    <button class="btn btn-primary" on:click={openCreateModal}>
      <Add size={16} />
      Create User
    </button>
  </div>

  {#if formSuccess}
    <div class="alert alert-success">{formSuccess}</div>
  {/if}

  {#if formError && !showCreateModal && !showEditModal && !showResetPasswordModal}
    <div class="alert alert-error">{formError}</div>
  {/if}

  <!-- Search -->
  <div class="search-bar">
    <Search size={16} />
    <input
      type="text"
      placeholder="Search users..."
      bind:value={searchQuery}
    />
  </div>

  {#if loading}
    <div class="loading">Loading users...</div>
  {:else if error}
    <div class="error-container">
      <p>Error: {error}</p>
      <button class="btn btn-secondary" on:click={loadUsers}>
        <Renew size={16} />
        Retry
      </button>
    </div>
  {:else}
    <div class="users-table-container">
      <table class="users-table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Name</th>
            <th>Email</th>
            <th>Team</th>
            <th>Role</th>
            <th>Status</th>
            <th>Last Login</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredUsers as user}
            <tr class:inactive={!user.is_active}>
              <td class="username">{user.username}</td>
              <td>{user.full_name || '-'}</td>
              <td>{user.email || '-'}</td>
              <td>{user.team || '-'}</td>
              <td>
                <span class="badge badge-{user.role}">{user.role}</span>
              </td>
              <td>
                <span class="status-indicator {user.is_active ? 'active' : 'inactive'}">
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
              </td>
              <td class="date">{formatDate(user.last_login)}</td>
              <td class="actions">
                <button class="btn-icon" title="Edit" on:click={() => openEditModal(user)}>
                  <Edit size={16} />
                </button>
                <button class="btn-icon" title="Reset Password" on:click={() => openResetPasswordModal(user)}>
                  <Password size={16} />
                </button>
                <button
                  class="btn-icon"
                  title="{user.is_active ? 'Deactivate' : 'Activate'}"
                  on:click={() => toggleUserStatus(user)}
                >
                  {#if user.is_active}
                    <Close size={16} />
                  {:else}
                    <Checkmark size={16} />
                  {/if}
                </button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <div class="table-footer">
      <span>Showing {filteredUsers.length} of {users.length} users</span>
    </div>
  {/if}
</div>

<!-- Create User Modal -->
{#if showCreateModal}
  <div class="modal-overlay" on:click={() => showCreateModal = false}>
    <div class="modal" on:click|stopPropagation>
      <div class="modal-header">
        <h2>Create New User</h2>
        <button class="btn-close" on:click={() => showCreateModal = false}>
          <Close size={20} />
        </button>
      </div>

      {#if formError}
        <div class="alert alert-error">{formError}</div>
      {/if}

      <form on:submit|preventDefault={createUser}>
        <div class="form-grid">
          <div class="form-group">
            <label for="username">Username *</label>
            <input type="text" id="username" bind:value={createForm.username} required />
          </div>
          <div class="form-group">
            <label for="password">Password *</label>
            <input type="password" id="password" bind:value={createForm.password} required />
          </div>
          <div class="form-group">
            <label for="email">Email</label>
            <input type="email" id="email" bind:value={createForm.email} />
          </div>
          <div class="form-group">
            <label for="full_name">Full Name</label>
            <input type="text" id="full_name" bind:value={createForm.full_name} />
          </div>
          <div class="form-group">
            <label for="team">Team</label>
            <input type="text" id="team" bind:value={createForm.team} />
          </div>
          <div class="form-group">
            <label for="department">Department</label>
            <input type="text" id="department" bind:value={createForm.department} />
          </div>
          <div class="form-group">
            <label for="language">Language</label>
            <input type="text" id="language" bind:value={createForm.language} placeholder="e.g., ko, en, ja" />
          </div>
          <div class="form-group">
            <label for="role">Role</label>
            <select id="role" bind:value={createForm.role}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
        </div>
        <div class="form-group checkbox">
          <input type="checkbox" id="must_change" bind:checked={createForm.must_change_password} />
          <label for="must_change">Require password change on first login</label>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" on:click={() => showCreateModal = false}>Cancel</button>
          <button type="submit" class="btn btn-primary">Create User</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Edit User Modal -->
{#if showEditModal && selectedUser}
  <div class="modal-overlay" on:click={() => showEditModal = false}>
    <div class="modal" on:click|stopPropagation>
      <div class="modal-header">
        <h2>Edit User: {selectedUser.username}</h2>
        <button class="btn-close" on:click={() => showEditModal = false}>
          <Close size={20} />
        </button>
      </div>

      {#if formError}
        <div class="alert alert-error">{formError}</div>
      {/if}

      <form on:submit|preventDefault={updateUser}>
        <div class="form-grid">
          <div class="form-group">
            <label for="edit_email">Email</label>
            <input type="email" id="edit_email" bind:value={editForm.email} />
          </div>
          <div class="form-group">
            <label for="edit_full_name">Full Name</label>
            <input type="text" id="edit_full_name" bind:value={editForm.full_name} />
          </div>
          <div class="form-group">
            <label for="edit_team">Team</label>
            <input type="text" id="edit_team" bind:value={editForm.team} />
          </div>
          <div class="form-group">
            <label for="edit_department">Department</label>
            <input type="text" id="edit_department" bind:value={editForm.department} />
          </div>
          <div class="form-group">
            <label for="edit_language">Language</label>
            <input type="text" id="edit_language" bind:value={editForm.language} placeholder="e.g., ko, en, ja" />
          </div>
          <div class="form-group">
            <label for="edit_role">Role</label>
            <select id="edit_role" bind:value={editForm.role}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
        </div>
        <div class="form-group checkbox">
          <input type="checkbox" id="edit_active" bind:checked={editForm.is_active} />
          <label for="edit_active">Account Active</label>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" on:click={() => showEditModal = false}>Cancel</button>
          <button type="submit" class="btn btn-primary">Save Changes</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Reset Password Modal -->
{#if showResetPasswordModal && selectedUser}
  <div class="modal-overlay" on:click={() => showResetPasswordModal = false}>
    <div class="modal modal-small" on:click|stopPropagation>
      <div class="modal-header">
        <h2>Reset Password: {selectedUser.username}</h2>
        <button class="btn-close" on:click={() => showResetPasswordModal = false}>
          <Close size={20} />
        </button>
      </div>

      {#if formError}
        <div class="alert alert-error">{formError}</div>
      {/if}

      <form on:submit|preventDefault={resetPassword}>
        <div class="form-group">
          <label for="new_password">New Password *</label>
          <input type="password" id="new_password" bind:value={resetPasswordForm.new_password} required />
        </div>
        <div class="form-group checkbox">
          <input type="checkbox" id="reset_must_change" bind:checked={resetPasswordForm.must_change_password} />
          <label for="reset_must_change">Require password change on next login</label>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" on:click={() => showResetPasswordModal = false}>Cancel</button>
          <button type="submit" class="btn btn-primary">Reset Password</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;
  }

  .header-content {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .page-title {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 1.5rem;
    font-weight: 600;
    color: #f4f4f4;
    margin: 0;
  }

  .page-subtitle {
    color: #8d8d8d;
    margin: 0;
  }

  .search-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 10px 16px;
    margin-bottom: 20px;
  }

  .search-bar input {
    flex: 1;
    background: transparent;
    border: none;
    color: #f4f4f4;
    font-size: 0.875rem;
    outline: none;
  }

  .search-bar input::placeholder {
    color: #6f6f6f;
  }

  .users-table-container {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    overflow: hidden;
  }

  .users-table {
    width: 100%;
    border-collapse: collapse;
  }

  .users-table th,
  .users-table td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid #2a2a2a;
  }

  .users-table th {
    background: #262626;
    color: #c6c6c6;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .users-table td {
    color: #f4f4f4;
    font-size: 0.875rem;
  }

  .users-table tr:hover {
    background: #262626;
  }

  .users-table tr.inactive {
    opacity: 0.6;
  }

  .username {
    font-weight: 600;
    color: #78a9ff;
  }

  .date {
    color: #8d8d8d;
    font-size: 0.8125rem;
  }

  .badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .badge-admin {
    background: #4589ff;
    color: #161616;
  }

  .badge-user {
    background: #393939;
    color: #c6c6c6;
  }

  .status-indicator {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8125rem;
  }

  .status-indicator::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .status-indicator.active::before {
    background: #24a148;
  }

  .status-indicator.inactive::before {
    background: #8d8d8d;
  }

  .actions {
    display: flex;
    gap: 8px;
  }

  .btn-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: transparent;
    border: 1px solid #393939;
    border-radius: 4px;
    color: #c6c6c6;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-icon:hover {
    background: #393939;
    color: #f4f4f4;
    border-color: #4589ff;
  }

  .btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    border-radius: 4px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
  }

  .btn-primary {
    background: #4589ff;
    color: #161616;
  }

  .btn-primary:hover {
    background: #78a9ff;
  }

  .btn-secondary {
    background: #393939;
    color: #f4f4f4;
  }

  .btn-secondary:hover {
    background: #4c4c4c;
  }

  .table-footer {
    padding: 12px 16px;
    color: #8d8d8d;
    font-size: 0.8125rem;
  }

  .loading {
    text-align: center;
    padding: 60px 20px;
    color: #c6c6c6;
  }

  .error-container {
    text-align: center;
    padding: 40px;
    color: #fa4d56;
  }

  .alert {
    padding: 12px 16px;
    border-radius: 4px;
    margin-bottom: 16px;
    font-size: 0.875rem;
  }

  .alert-success {
    background: #042f1a;
    border: 1px solid #24a148;
    color: #42be65;
  }

  .alert-error {
    background: #2d0709;
    border: 1px solid #fa4d56;
    color: #ff8389;
  }

  /* Modal Styles */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    width: 90%;
    max-width: 600px;
    max-height: 90vh;
    overflow-y: auto;
  }

  .modal-small {
    max-width: 400px;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    border-bottom: 1px solid #2a2a2a;
  }

  .modal-header h2 {
    color: #f4f4f4;
    font-size: 1.125rem;
    font-weight: 600;
    margin: 0;
  }

  .btn-close {
    background: transparent;
    border: none;
    color: #8d8d8d;
    cursor: pointer;
    padding: 4px;
  }

  .btn-close:hover {
    color: #f4f4f4;
  }

  .modal form {
    padding: 24px;
  }

  .form-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 16px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .form-group.checkbox {
    flex-direction: row;
    align-items: center;
    gap: 10px;
  }

  .form-group label {
    color: #c6c6c6;
    font-size: 0.8125rem;
  }

  .form-group input[type="text"],
  .form-group input[type="email"],
  .form-group input[type="password"],
  .form-group select {
    background: #262626;
    border: 1px solid #393939;
    border-radius: 4px;
    padding: 10px 12px;
    color: #f4f4f4;
    font-size: 0.875rem;
  }

  .form-group input:focus,
  .form-group select:focus {
    outline: none;
    border-color: #4589ff;
  }

  .form-group input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: #4589ff;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    padding-top: 16px;
    border-top: 1px solid #2a2a2a;
    margin-top: 16px;
  }

  @media (max-width: 640px) {
    .form-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
