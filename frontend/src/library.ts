/**
 * Local-storage-backed list of teacher tokens (courses + standalone lessons)
 * the teacher has added to their library. Until proper teacher accounts ship,
 * this is the per-browser "my courses" persistence layer.
 *
 * Future: when accounts land, this same shape becomes `GET /me/library` from
 * the server and the localStorage version becomes an offline cache.
 */

const LIBRARY_KEY = 'cadence.library';

export type LibraryKind = 'course' | 'lesson';

export interface LibraryEntry {
  token: string;
  kind: LibraryKind;
  name: string;
  join_code?: string;
  added_at: string;
  // Marker for demo/seed entries so the UI can label them and de-duplicate
  // when the logged-in teacher's own courses arrive from the server.
  demo?: boolean;
}

function read(): LibraryEntry[] {
  try {
    const raw = localStorage.getItem(LIBRARY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(items: LibraryEntry[]): void {
  try {
    localStorage.setItem(LIBRARY_KEY, JSON.stringify(items));
  } catch {
    // ignore quota / disabled-storage
  }
}

export function getLibrary(): LibraryEntry[] {
  return read();
}

export function addToLibrary(entry: Omit<LibraryEntry, 'added_at'>): LibraryEntry[] {
  const items = read();
  // Deduplicate by token — keep the existing entry if it's already there
  if (items.some((e) => e.token === entry.token)) return items;
  const fresh: LibraryEntry = { ...entry, added_at: new Date().toISOString() };
  const next = [fresh, ...items];
  write(next);
  return next;
}

export function removeFromLibrary(token: string): LibraryEntry[] {
  const next = read().filter((e) => e.token !== token);
  write(next);
  return next;
}

export function clearLibrary(): void {
  write([]);
}
