/**
 * Node >= 22 exposes an experimental `localStorage` binding on globalThis
 * (undefined unless --localstorage-file is provided). Vitest skips copying
 * jsdom's implementation when the key already exists on the global, so we
 * install a tiny in-memory fallback to keep the app's token storage — and
 * the i18n language persistence — testable.
 *
 * This module must be imported *before* anything that touches localStorage
 * (see setup.js import order).
 */
if (typeof globalThis.localStorage === "undefined" || !globalThis.localStorage) {
  const store = new Map();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    writable: true,
    value: {
      getItem: (key) => (store.has(String(key)) ? store.get(String(key)) : null),
      setItem: (key, value) => {
        store.set(String(key), String(value));
      },
      removeItem: (key) => {
        store.delete(String(key));
      },
      clear: () => {
        store.clear();
      },
      key: (index) => [...store.keys()][index] ?? null,
      get length() {
        return store.size;
      },
    },
  });
}

export {};
