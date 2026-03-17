<script context="module">
  /**
   * MapIcons - SVG path data for world map node type icons.
   * Returns {path, size} for each node type.
   * All icons are inline SVG -- no external files.
   *
   * Phase 38: Fantasy World Map (Plan 02)
   */

  /** @type {Record<string, {path: string, size: number}>} */
  export const NODE_ICONS = {
    Town: {
      // Castle turret silhouette
      path: 'M4 20h16v-2H4v2zm2-4h2v-4H6v4zm4 0h4v-6h-4v6zm6 0h2v-4h-2v4zM4 12h16v-2H4v2zm4-6v2h8V6l-4-4-4 4z',
      size: 24
    },
    Dungeon: {
      // Skull
      path: 'M12 2C6.48 2 2 6.48 2 12c0 3.69 2.04 6.9 5.05 8.59L8 18h2v-2H8v-2h2v-1c-1.66 0-3-1.34-3-3 0-1.3.84-2.4 2-2.82V6h2v1.18c1.16.42 2 1.52 2 2.82 0 1.66-1.34 3-3 3v1h2v2h-2v2h2l.95 2.59C17.96 18.9 20 15.69 20 12c0-5.52-4.48-10-10-10zM9 11c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm6 0c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z',
      size: 24
    },
    Fortress: {
      // Shield
      path: 'M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 2.18l7 3.12v4.7c0 4.67-3.13 9.06-7 10.2-3.87-1.14-7-5.53-7-10.2V6.3l7-3.12z',
      size: 24
    },
    Wilderness: {
      // Tent / camp
      path: 'M12 3L1 21h22L12 3zm0 4.24L18.76 19H14v-4h-4v4H5.24L12 7.24z',
      size: 24
    },
    Main: {
      // Compass rose (larger)
      path: 'M12 2l3 6.5L22 12l-7 3.5L12 22l-3-6.5L2 12l7-3.5L12 2zm0 4.47L10.26 11 6.5 12l3.76 1L12 17.53 13.74 13l3.76-1-3.76-1L12 6.47z',
      size: 28
    },
    Sub: {
      // Tree
      path: 'M12 2L6 10h3v3H6l6 8 6-8h-3v-3h3L12 2zm0 3.54L15.08 10H13v3h2.08L12 17.46 8.92 13H11v-3H8.92L12 5.54z',
      size: 20
    }
  };

  /**
   * Get icon data for a region type, with fallback to a circle.
   * @param {string} regionType
   * @returns {{path: string, size: number}}
   */
  export function getNodeIcon(regionType) {
    return NODE_ICONS[regionType] || { path: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z', size: 20 };
  }
</script>
