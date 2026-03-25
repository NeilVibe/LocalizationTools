/**
 * Map translation status to display tag type.
 * 3-state scheme: teal=confirmed, warm-gray=draft, gray=empty.
 *
 * NOTE: Phase 84 GRID-07 will expand this into full StatusColors module.
 * Keep this extraction minimal per D-16.
 */
export function getStatusKind(status: string | undefined | null): string {
  switch (status) {
    case 'approved': return 'teal';
    case 'reviewed': return 'teal';
    case 'translated': return 'warm-gray';
    default: return 'gray';
  }
}
