<script>
  /**
   * CodexCard.svelte - Glassmorphism entity card with parallax hover
   *
   * Features:
   * - Glassmorphism: backdrop-filter blur + semi-transparent background
   * - Parallax hover: mousemove-driven perspective tilt (max +/-5deg)
   * - Shimmer-to-reveal: CSS transition on image load
   * - Staggered entrance: CSS transition with delay based on card index
   * - prefers-reduced-motion: disables all motion effects
   *
   * Phase 39: Codex Cards + Relationship Graph (Plan 01)
   */
  import { Tag } from "carbon-components-svelte";
  import PlaceholderImage from "$lib/components/ldm/PlaceholderImage.svelte";

  // Type badge colors (matching CodexPage)
  const TYPE_COLORS = {
    character: 'purple',
    item: 'cyan',
    skill: 'magenta',
    region: 'teal',
    gimmick: 'warm-gray'
  };

  let { entity, index = 0, apiBase = '', failedImages = new Set(), onclick = () => {}, onfailimage = () => {} } = $props();

  let cardEl = $state(null);
  let visible = $state(false);
  let imageLoaded = $state(false);
  let prefersReducedMotion = $state(false);

  // Check reduced motion preference
  $effect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    prefersReducedMotion = mq.matches;
    const handler = (e) => { prefersReducedMotion = e.matches; };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  });

  // Staggered entrance: add .visible class after mount
  $effect(() => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        visible = true;
      });
    });
  });

  // Parallax hover via mousemove/mouseleave
  $effect(() => {
    const el = cardEl;
    if (!el || prefersReducedMotion) return;

    const heroImg = el.querySelector('.card-hero-image');

    function onMouseMove(e) {
      const rect = el.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const relX = (e.clientX - centerX) / (rect.width / 2); // -1 to 1
      const relY = (e.clientY - centerY) / (rect.height / 2); // -1 to 1

      const rotateY = relX * 5; // max +/-5deg
      const rotateX = -relY * 5; // max +/-5deg (invert Y for natural tilt)

      el.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
      if (heroImg) {
        heroImg.style.transform = `translate(${-rotateY * 2}px, ${rotateX * 2}px)`;
      }
    }

    function onMouseLeave() {
      el.style.transform = '';
      if (heroImg) {
        heroImg.style.transform = '';
      }
    }

    el.addEventListener('mousemove', onMouseMove);
    el.addEventListener('mouseleave', onMouseLeave);

    return () => {
      el.removeEventListener('mousemove', onMouseMove);
      el.removeEventListener('mouseleave', onMouseLeave);
    };
  });

  // Image resolution: ai_image_url > image_texture thumbnail > PlaceholderImage
  let aiImageKey = $derived('ai_' + entity.strkey);
  let textureKey = $derived(entity.strkey);
  let useAiImage = $derived(entity.ai_image_url && !failedImages.has(aiImageKey));
  let useTexture = $derived(!useAiImage && entity.image_texture && !failedImages.has(textureKey));
  let usePlaceholder = $derived(!useAiImage && !useTexture);

  let imageSrc = $derived(
    useAiImage
      ? `${apiBase}${entity.ai_image_url}?v=${Date.now()}`
      : useTexture
        ? `${apiBase}/api/ldm/mapdata/thumbnail/${entity.image_texture}?v=${Date.now()}`
        : null
  );

  function handleImageLoad() {
    imageLoaded = true;
  }

  function handleImageError() {
    if (useAiImage) {
      onfailimage(aiImageKey);
    } else if (useTexture) {
      onfailimage(textureKey);
    }
  }

  // Related entity count
  let refCount = $derived(entity.related_entities?.length ?? 0);

  // Clean description (strip br tags)
  let cleanDesc = $derived(
    entity.description ? entity.description.replace(/<br\s*\/?>/gi, ' ') : ''
  );
</script>

<button
  class="codex-card"
  class:visible
  style="--card-index: {index}"
  bind:this={cardEl}
  onclick={onclick}
  aria-label="View {entity.name} ({entity.entity_type})"
>
  <!-- Hero Image Area -->
  <div class="card-hero">
    {#if usePlaceholder}
      <div class="card-hero-image placeholder-wrapper">
        <PlaceholderImage entityType={entity.entity_type} entityName={entity.name} />
      </div>
    {:else}
      <div class="shimmer-bg" class:hidden={imageLoaded}></div>
      <img
        src={imageSrc}
        alt={entity.name}
        class="card-hero-image"
        class:loaded={imageLoaded}
        loading="lazy"
        onload={handleImageLoad}
        onerror={handleImageError}
      />
    {/if}
    <!-- Type badge -->
    <div class="card-badge">
      <Tag type={TYPE_COLORS[entity.entity_type] || 'gray'} size="sm">
        {entity.entity_type}
      </Tag>
    </div>
  </div>

  <!-- Card Body -->
  <div class="card-body">
    <span class="card-name">{entity.name}</span>
    {#if cleanDesc}
      <span class="card-desc">{cleanDesc}</span>
    {/if}
    <div class="card-stats">
      {#if refCount > 0}
        <span class="card-refs">{refCount} refs</span>
      {/if}
    </div>
  </div>
</button>

<style>
  .codex-card {
    background: rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(212, 154, 92, 0.2);
    border-radius: 12px;
    overflow: hidden;
    cursor: pointer;
    position: relative;
    text-align: left;
    color: var(--cds-text-01);
    padding: 0;
    display: flex;
    flex-direction: column;
    transition: transform 200ms cubic-bezier(0.25, 1, 0.5, 1),
                box-shadow 200ms cubic-bezier(0.25, 1, 0.5, 1);

    /* Entrance: start hidden */
    opacity: 0;
    transform: translateY(16px);
  }

  .codex-card.visible {
    opacity: 1;
    transform: translateY(0);
    transition: opacity 400ms cubic-bezier(0.25, 1, 0.5, 1),
                transform 400ms cubic-bezier(0.25, 1, 0.5, 1),
                box-shadow 200ms cubic-bezier(0.25, 1, 0.5, 1);
    transition-delay: calc(var(--card-index) * 60ms);
  }

  .codex-card:hover {
    box-shadow: 0 8px 32px rgba(212, 154, 92, 0.15);
  }

  .codex-card:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  /* Hero image area */
  .card-hero {
    position: relative;
    width: 100%;
    height: 160px;
    overflow: hidden;
    background: var(--cds-layer-02);
  }

  .card-hero-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0;
    transition: opacity 400ms cubic-bezier(0.25, 1, 0.5, 1),
                transform 200ms cubic-bezier(0.25, 1, 0.5, 1);
  }

  .card-hero-image.loaded {
    opacity: 1;
  }

  .placeholder-wrapper {
    opacity: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* Shimmer placeholder */
  .shimmer-bg {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.03) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
  }

  .shimmer-bg.hidden {
    opacity: 0;
    transition: opacity 300ms ease;
  }

  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  /* Type badge */
  .card-badge {
    position: absolute;
    top: 8px;
    right: 8px;
  }

  /* Card body */
  .card-body {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
  }

  .card-name {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .card-desc {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    line-height: 1.4;
  }

  .card-stats {
    display: flex;
    gap: 8px;
    margin-top: auto;
    padding-top: 4px;
  }

  .card-refs {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    background: var(--cds-layer-02);
    padding: 1px 6px;
    border-radius: 8px;
  }

  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    .codex-card {
      opacity: 1;
      transform: none;
      transition: none;
    }
    .codex-card.visible {
      transition: none;
    }
    .card-hero-image {
      opacity: 1;
      transition: none;
    }
    .shimmer-bg {
      animation: none;
    }
  }
</style>
