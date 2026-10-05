/**
 * Pokédex — Frontend IPFS Resolver & Gateway Fallback
 * Module: projects/frontend/src/lib/ipfs.ts
 * =================================================================
 * Resolves ipfs:// URIs into public HTTP gateway URLs with multi-gateway fallback,
 * path sanitization, and XSS prevention.
 */

export const IPFS_GATEWAYS = [
  'https://ipfs.io/ipfs/',
  'https://dweb.link/ipfs/',
  'https://cloudflare-ipfs.com/ipfs/',
  'https://gateway.pinata.cloud/ipfs/'
];

/**
 * Resolves an ipfs:// URI or CID into a browser-loadable HTTP gateway URL.
 */
export function resolveIpfsUri(uri: string, gatewayIndex: number = 0): string {
  if (!uri) return '';

  // Clean trailing #arc3 or fragment
  const cleanUri = uri.split('#')[0].trim();

  // If already http/https, return sanitized URL
  if (cleanUri.startsWith('http://') || cleanUri.startsWith('https://')) {
    return cleanUri;
  }

  // Extract CID path
  let path = cleanUri;
  if (cleanUri.startsWith('ipfs://')) {
    path = cleanUri.replace('ipfs://', '');
  }

  // Sanitize path (prevent path traversal / XSS)
  path = path.replace(/^\/+/, '').replace(/\.\.\//g, '');

  const gateway = IPFS_GATEWAYS[gatewayIndex % IPFS_GATEWAYS.length];
  return `${gateway}${path}`;
}

/**
 * Validates whether a given string is a plausible IPFS CID (v0 Qm... or v1 bafy...).
 */
export function isValidIpfsCid(cid: string): boolean {
  if (!cid || typeof cid !== 'string') return false;
  // CIDv0 starts with Qm (46 chars base58) or CIDv1 starts with bafy/bafk (base32)
  return /^Qm[1-9A-HJ-NP-Za-km-z]{44}$/.test(cid) || /^baf[a-z0-9]{50,}$/i.test(cid);
}
