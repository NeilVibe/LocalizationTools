<script>
  /**
   * PlaceholderAudio.svelte - Waveform SVG audio placeholder with entity name
   *
   * Renders a deterministic waveform visualization when entity audio is missing.
   * Bar heights are derived from sine wave for consistent visual pattern.
   *
   * Phase 21: AI Naming Coherence + Placeholders (Plan 02)
   */

  // Props
  let { entityName = '' } = $props();

  // Display label
  let displayLabel = $derived(entityName || '[No Audio]');

  // Generate 20 bars with sine-based heights
  const bars = Array.from({ length: 20 }, (_, i) => ({
    x: i * 10 + 2,
    height: Math.sin(i * 0.8) * 24 + 8,
    y: 20 - (Math.sin(i * 0.8) * 24 + 8) / 2
  }));
</script>

<div class="placeholder-audio">
  <svg viewBox="0 0 200 40" xmlns="http://www.w3.org/2000/svg" class="waveform">
    {#each bars as bar, i (i)}
      <rect
        x={bar.x}
        y={bar.y}
        width="6"
        height={bar.height}
        rx="2"
        fill="var(--cds-text-03)"
        opacity="0.3"
      />
    {/each}
  </svg>
  <span class="audio-label">{displayLabel}</span>
</div>

<style>
  .placeholder-audio {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }

  .waveform {
    width: 100%;
    max-width: 200px;
    height: 40px;
  }

  .audio-label {
    font-size: 12px;
    color: var(--cds-text-03);
    font-style: italic;
  }
</style>
