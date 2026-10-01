import { isNativeApp } from "./native";

/**
 * Registers the service worker — production only, so the dev server is
 * never haunted by a stale cache. The Capacitor shell ships a local bundle
 * and WebView push doesn't work, so it never registers one either.
 *
 * Both dependencies are injectable for tests.
 */
export function registerServiceWorker({
  prod = import.meta.env.PROD,
  serviceWorker = typeof navigator !== "undefined" ? navigator.serviceWorker : undefined,
} = {}) {
  if (!prod || !serviceWorker || isNativeApp()) return Promise.resolve(null);
  return serviceWorker.register("/sw.js").catch(() => null);
}
