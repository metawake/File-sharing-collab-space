export function extractDriveIds(input: string): string[] {
  const parts = input
    .split(/[,\n\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);

  const ids: string[] = [];
  for (const p of parts) {
    try {
      if (p.includes('drive.google.com')) {
        // /file/d/<ID>/...
        const m1 = p.match(/\/file\/d\/([A-Za-z0-9_-]+)/);
        if (m1?.[1]) {
          ids.push(m1[1]);
          continue;
        }
        // open?id=<ID>
        const url = new URL(p);
        const idParam = url.searchParams.get('id');
        if (idParam) {
          ids.push(idParam);
          continue;
        }
      }
      // Looks like a raw ID
      ids.push(p);
    } catch {
      // Fallback to raw
      ids.push(p);
    }
  }
  // de-dup while keeping order
  return Array.from(new Set(ids));
}

