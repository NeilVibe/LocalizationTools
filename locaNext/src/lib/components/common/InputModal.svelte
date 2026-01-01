<script>
  /**
   * InputModal.svelte - Carbon Design System Input Modal
   *
   * Clean, professional input dialog replacing ugly browser prompt().
   * Used for: Create project, Create folder, Rename items.
   */
  import { Modal, TextInput } from 'carbon-components-svelte';

  // Props
  let {
    open = $bindable(false),
    title = 'Enter Value',
    label = 'Name',
    placeholder = '',
    value = $bindable(''),
    submitLabel = 'Create',
    danger = false,
    onSubmit = () => {},
    onCancel = () => {}
  } = $props();

  // Internal state
  let inputValue = $state('');
  let inputRef = $state(null);

  // Sync with prop value when opened
  $effect(() => {
    if (open) {
      inputValue = value || '';
      // Focus input after modal opens
      setTimeout(() => {
        if (inputRef) {
          inputRef.focus();
          inputRef.select();
        }
      }, 100);
    }
  });

  function handleSubmit() {
    if (!inputValue.trim()) return;
    value = inputValue.trim();
    onSubmit(inputValue.trim());
    open = false;
  }

  function handleCancel() {
    onCancel();
    open = false;
  }

  function handleKeydown(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleSubmit();
    }
  }
</script>

<Modal
  bind:open
  modalHeading={title}
  primaryButtonText={submitLabel}
  secondaryButtonText="Cancel"
  {danger}
  on:click:button--primary={handleSubmit}
  on:click:button--secondary={handleCancel}
  on:close={handleCancel}
  size="sm"
>
  <TextInput
    bind:ref={inputRef}
    bind:value={inputValue}
    labelText={label}
    {placeholder}
    on:keydown={handleKeydown}
  />
</Modal>
