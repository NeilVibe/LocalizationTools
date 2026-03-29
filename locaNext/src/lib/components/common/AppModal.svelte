<script>
  /**
   * AppModal.svelte -- Svelte 5 wrapper around Carbon Modal (Svelte 4)
   *
   * Phase 99, Plan 01: This is the ONLY file in the codebase that uses
   * on:click:button--primary / on:click:button--secondary syntax.
   * All application code uses pure Svelte 5 callback props instead.
   *
   * Purpose: Isolates the Carbon 0.95 (Svelte 4) compatibility boundary
   * to ONE file. Consumers use onprimary/onsecondary/onclose callbacks.
   */
  import { Modal } from 'carbon-components-svelte';

  let {
    open = $bindable(false),
    size = undefined,
    danger = false,
    alert = false,
    passiveModal = false,
    modalHeading = undefined,
    modalLabel = undefined,
    modalAriaLabel = undefined,
    iconDescription = 'Close',
    hasForm = false,
    hasScrollingContent = false,
    primaryButtonText = '',
    primaryButtonDisabled = false,
    primaryButtonIcon = undefined,
    secondaryButtonText = '',
    secondaryButtons = [],
    selectorPrimaryFocus = '[data-modal-primary-focus]',
    preventCloseOnClickOutside = false,
    shouldSubmitOnEnter = true,
    id = undefined,
    ref = undefined,
    onprimary = () => {},
    onsecondary = () => {},
    onclose = () => {},
    children,
    ...restProps
  } = $props();
</script>

<Modal
  bind:open
  {size}
  {danger}
  {alert}
  {passiveModal}
  {modalHeading}
  {modalLabel}
  {modalAriaLabel}
  {iconDescription}
  {hasForm}
  {hasScrollingContent}
  {primaryButtonText}
  {primaryButtonDisabled}
  {primaryButtonIcon}
  {secondaryButtonText}
  {secondaryButtons}
  {selectorPrimaryFocus}
  {preventCloseOnClickOutside}
  {shouldSubmitOnEnter}
  {id}
  {ref}
  {...restProps}
  on:click:button--primary={onprimary}
  on:click:button--secondary={onsecondary}
  on:close={onclose}
>
  {@render children?.()}
</Modal>
