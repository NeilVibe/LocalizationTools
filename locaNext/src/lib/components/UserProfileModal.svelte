<script>
  /**
   * UI-038: User Profile Modal
   * Shows user profile details when clicking on username in user menu.
   */
  import { Modal, StructuredList, StructuredListHead, StructuredListRow, StructuredListCell, StructuredListBody, Tag } from "carbon-components-svelte";
  import { User as UserIcon } from "carbon-icons-svelte";
  import { user } from "$lib/stores/app.js";

  let { open = $bindable(false) } = $props();

  // Role color mapping
  function getRoleKind(role) {
    switch (role) {
      case 'superadmin': return 'red';
      case 'admin': return 'purple';
      default: return 'blue';
    }
  }
</script>

<Modal
  bind:open
  modalHeading="User Profile"
  passiveModal
  size="sm"
>
  <div class="profile-content">
    <div class="profile-header">
      <div class="avatar">
        <UserIcon size={48} />
      </div>
      <div class="user-info">
        <h3>{$user?.full_name || $user?.username || 'User'}</h3>
        <Tag kind={getRoleKind($user?.role)}>{$user?.role || 'user'}</Tag>
      </div>
    </div>

    <StructuredList>
      <StructuredListHead>
        <StructuredListRow head>
          <StructuredListCell head>Field</StructuredListCell>
          <StructuredListCell head>Value</StructuredListCell>
        </StructuredListRow>
      </StructuredListHead>
      <StructuredListBody>
        <StructuredListRow>
          <StructuredListCell>Username</StructuredListCell>
          <StructuredListCell>{$user?.username || '-'}</StructuredListCell>
        </StructuredListRow>
        {#if $user?.email}
          <StructuredListRow>
            <StructuredListCell>Email</StructuredListCell>
            <StructuredListCell>{$user.email}</StructuredListCell>
          </StructuredListRow>
        {/if}
        <StructuredListRow>
          <StructuredListCell>Team</StructuredListCell>
          <StructuredListCell>{$user?.team || '-'}</StructuredListCell>
        </StructuredListRow>
        <StructuredListRow>
          <StructuredListCell>Department</StructuredListCell>
          <StructuredListCell>{$user?.department || '-'}</StructuredListCell>
        </StructuredListRow>
        <StructuredListRow>
          <StructuredListCell>Language</StructuredListCell>
          <StructuredListCell>{$user?.language || '-'}</StructuredListCell>
        </StructuredListRow>
      </StructuredListBody>
    </StructuredList>
  </div>
</Modal>

<style>
  .profile-content {
    padding: 0.5rem 0;
  }

  .profile-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .avatar {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: var(--cds-layer-02);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--cds-text-02);
  }

  .user-info h3 {
    margin: 0 0 0.5rem 0;
    font-size: 1.25rem;
    font-weight: 600;
  }
</style>
