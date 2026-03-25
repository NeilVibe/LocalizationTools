import { describe, it, expect } from 'vitest';
import { getStatusKind } from '../src/lib/utils/statusColors';

describe('getStatusKind', () => {
  it('returns teal for approved', () => expect(getStatusKind('approved')).toBe('teal'));
  it('returns teal for reviewed', () => expect(getStatusKind('reviewed')).toBe('teal'));
  it('returns warm-gray for translated', () => expect(getStatusKind('translated')).toBe('warm-gray'));
  it('returns gray for unknown string', () => expect(getStatusKind('unknown')).toBe('gray'));
  it('returns gray for undefined', () => expect(getStatusKind(undefined)).toBe('gray'));
  it('returns gray for null', () => expect(getStatusKind(null)).toBe('gray'));
  it('returns gray for empty string', () => expect(getStatusKind('')).toBe('gray'));
});
