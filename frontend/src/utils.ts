/**
 * Utility functions for LM-Screen frontend
 */

/**
 * Safely format any field value (string, number, array, or object) into a human-readable string.
 * Prevents "Objects are not valid as a React child" crashes when backend extractors return
 * structured objects or arrays (e.g. [{ type: 'LICENSE', number: '...' }] for certifications).
 */
export function formatFieldValue(val: any): string {
  if (val === null || val === undefined || val === '') return '—';
  if (typeof val === 'string') return val;
  if (typeof val === 'number' || typeof val === 'boolean') return String(val);

  if (Array.isArray(val)) {
    if (val.length === 0) return '—';
    return val
      .map((item) => {
        if (item === null || item === undefined) return '';
        if (typeof item === 'object') {
          if (item.type && item.number) return `${item.type}: ${item.number}`;
          if (item.name && item.value) return `${item.name}: ${item.value}`;
          if (item.name) return String(item.name);
          if (item.label && item.value) return `${item.label}: ${item.value}`;
          return Object.entries(item)
            .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`)
            .join(', ');
        }
        return String(item);
      })
      .filter(Boolean)
      .join('; ');
  }

  if (typeof val === 'object') {
    if (val.type && val.number) return `${val.type}: ${val.number}`;
    if (val.name && val.value) return `${val.name}: ${val.value}`;
    if (val.name) return String(val.name);
    if (val.label && val.value) return `${val.label}: ${val.value}`;
    return Object.entries(val)
      .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`)
      .join(', ');
  }

  return String(val);
}
