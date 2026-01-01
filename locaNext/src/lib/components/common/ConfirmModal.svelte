<script>
  /**
   * ConfirmModal.svelte - Carbon Design System Confirm Modal
   *
   * Clean, professional confirm dialog replacing ugly browser confirm().
   * Used for: Delete confirmation, destructive actions.
   */
  import { Modal } from 'carbon-components-svelte';

  // Props
  let {
    open = $bindable(false),
    title = 'Confirm Action',
    message = 'Are you sure?',
    confirmLabel = 'Confirm',
    cancelLabel = 'Cancel',
    danger = true,
    onConfirm = () => {},
    onCancel = () => {}
  } = $props();

  function handleConfirm() {
    onConfirm();
    open = false;
  }

  function handleCancel() {
    onCancel();
    open = false;
  }
</script>

<Modal
  bind:open
  modalHeading={title}
  primaryButtonText={confirmLabel}
  secondaryButtonText={cancelLabel}
  {danger}
  on:click:button--primary={handleConfirm}
  on:click:button--secondary={handleCancel}
  on:close={handleCancel}
  size="sm"
>
  <p class="confirm-message">{message}</p>
</Modal>

<style>
  .confirm-message {
    margin: 0;
    font-size: 0.875rem;
    line-height: 1.5;
    color: var(--cds-text-01);
  }
</style>
