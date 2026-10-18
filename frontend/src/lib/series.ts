/** Thins a long series to at most `max` points, always keeping the first and last, so sparklines stay light. */
export function smoothHistory<T>(points: readonly T[], max: number): T[] {
  if (points.length <= max) return [...points];
  const out: T[] = [];
  const step = (points.length - 1) / (max - 1);
  for (let i = 0; i < max; i++) {
    const p = points[Math.round(i * step)];
    if (p !== undefined) out.push(p);
  }
  return out;
}
