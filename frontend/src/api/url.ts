// An explicit hierarchical scheme, e.g. "https://".
const HIERARCHICAL_SCHEME = /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//;

// An opaque scheme with no "//" authority — "javascript:alert(1)", "data:...".
// These must be left alone so the backend's allowlist can reject them; adding
// "https://" would launder a javascript: payload into a URL that validates.
// The negative lookahead spares "example.com:8080/x", where the colon is a port.
const OPAQUE_SCHEME = /^[a-zA-Z][a-zA-Z0-9+.-]*:(?!\d)/;

/**
 * Add a default `https://` when the user omitted the scheme.
 *
 * Mirrors `normalise_url` in `backend/app/services/tor_service.py` so what the
 * form shows matches what the server stores. Non-technical submitters type
 * "www.unsw.edu.au/tor"; rejecting that is needless friction.
 */
export function normaliseUrl(url: string): string {
  const cleaned = url.trim();
  if (!cleaned) return cleaned;
  if (HIERARCHICAL_SCHEME.test(cleaned) || OPAQUE_SCHEME.test(cleaned)) return cleaned;
  return `https://${cleaned}`;
}
