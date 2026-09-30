/**
 * Registers the service worker — production only, so the dev server is
 * never haunted by a stale cache.
 *
 * Both dependencies are injectable for tests.
 */
export function registerServiceWorker({
  prod = import.meta.env.PROD,
  serviceWorker = typeof navigator !== "undefined" ? navigator.serviceWorker : undefined,
} = {}) {
  if (!prod || !serviceWorker) return Promise.resolve(null);
  return serviceWorker.register("/sw.js").catch(() => null);
}
