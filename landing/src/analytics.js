/**
 * Privacy-friendly analytics (Plausible-compatible: script + data-domain).
 *
 * Injected only in production builds and only when VITE_ANALYTICS_SRC is
 * provided at build time — dev and tests never load anything. No cookies,
 * so no consent banner is required.
 */
export function initAnalytics() {
  const src = import.meta.env.VITE_ANALYTICS_SRC;
  if (!import.meta.env.PROD || !src) return;
  const script = document.createElement("script");
  script.defer = true;
  script.src = src;
  const domain = import.meta.env.VITE_ANALYTICS_DOMAIN;
  if (domain) script.setAttribute("data-domain", domain);
  document.head.appendChild(script);
}
