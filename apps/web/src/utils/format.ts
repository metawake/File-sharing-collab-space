export function formatBytes(bytes?: number | string | null): string {
  if (bytes === null || bytes === undefined) return '—';
  const n = typeof bytes === 'string' ? parseInt(bytes, 10) : bytes;
  if (!Number.isFinite(n) || isNaN(n as number) || (n as number) < 0) return '—';
  const b = n as number;
  if (b < 1024) return `${b} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = b / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i++;
  }
  const fixed = value < 10 ? value.toFixed(1) : Math.round(value).toString();
  return `${fixed} ${units[i]}`;
}

