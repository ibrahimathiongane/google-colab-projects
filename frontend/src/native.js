/**
 * True inside the Capacitor native shell (Android/iOS WebView).
 * The web build never defines `window.Capacitor`, so this is false there.
 * The `win` argument is injectable for tests.
 */
export function isNativeApp(
  win = typeof window !== "undefined" ? window : undefined,
) {
  return win?.Capacitor?.isNativePlatform?.() === true;
}
