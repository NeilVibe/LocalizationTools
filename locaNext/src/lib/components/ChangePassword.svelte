<script>
  import {
    Modal,
    Form,
    FormGroup,
    TextInput,
    Button,
    InlineNotification
  } from "carbon-components-svelte";
  import { api } from "$lib/api/client.js";
  import { logger } from "$lib/utils/logger.js";

  // Svelte 5: Props
  let { open = $bindable(false) } = $props();

  // Svelte 5: State
  let currentPassword = $state('');
  let newPassword = $state('');
  let confirmPassword = $state('');
  let loading = $state(false);
  let error = $state(null);
  let success = $state(false);

  function resetForm() {
    currentPassword = '';
    newPassword = '';
    confirmPassword = '';
    error = null;
    success = false;
    loading = false;
  }

  function handleClose() {
    resetForm();
    open = false;
  }

  async function handleSubmit() {
    // Validate passwords match
    if (newPassword !== confirmPassword) {
      error = 'New passwords do not match';
      return;
    }

    // Validate password length
    if (newPassword.length < 4) {
      error = 'Password must be at least 4 characters';
      return;
    }

    loading = true;
    error = null;

    try {
      logger.userAction("Password change requested");
      await api.changePassword(currentPassword, newPassword, confirmPassword);

      logger.success("Password changed successfully");
      success = true;

      // Close modal after a short delay
      setTimeout(() => {
        handleClose();
      }, 2000);
    } catch (err) {
      logger.error("Password change failed", { error: err.message });
      error = err.message;
    } finally {
      loading = false;
    }
  }
</script>

<Modal
  bind:open
  modalHeading="Change Password"
  primaryButtonText="Change Password"
  secondaryButtonText="Cancel"
  primaryButtonDisabled={loading || success}
  on:click:button--secondary={handleClose}
  on:close={handleClose}
  on:submit={handleSubmit}
  size="sm"
>
  {#if success}
    <InlineNotification
      kind="success"
      title="Success"
      subtitle="Your password has been changed successfully."
      hideCloseButton
    />
  {:else}
    {#if error}
      <InlineNotification
        kind="error"
        title="Error"
        subtitle={error}
        on:close={() => error = null}
      />
    {/if}

    <Form on:submit={handleSubmit}>
      <FormGroup legendText="">
        <TextInput
          id="current-password"
          type="password"
          labelText="Current Password"
          placeholder="Enter your current password"
          bind:value={currentPassword}
          required
          disabled={loading}
        />
      </FormGroup>

      <FormGroup legendText="">
        <TextInput
          id="new-password"
          type="password"
          labelText="New Password"
          placeholder="Enter your new password"
          bind:value={newPassword}
          required
          disabled={loading}
        />
      </FormGroup>

      <FormGroup legendText="">
        <TextInput
          id="confirm-password"
          type="password"
          labelText="Confirm New Password"
          placeholder="Confirm your new password"
          bind:value={confirmPassword}
          required
          disabled={loading}
          invalid={confirmPassword && newPassword !== confirmPassword}
          invalidText="Passwords do not match"
        />
      </FormGroup>
    </Form>
  {/if}
</Modal>

<style>
  :global(.bx--modal-content) {
    padding-top: 1rem;
  }

  :global(.bx--form-item) {
    margin-bottom: 1rem;
  }
</style>
