/**
 * Build-time SEO artifacts for the landing page.
 *
 * - absolutises the __SITE_URL__ tokens in dist/index.html (og:url, og:image)
 * - injects the canonical URL
 * - writes dist/robots.txt (with an absolute Sitemap line) and dist/sitemap.xml
 *
 * Pure helpers are exported for tests; the plugin runs on `vite build` only.
 */
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export function absolutiseHtml(html, site) {
  let out = html.replaceAll("__SITE_URL__", site);
  if (!out.includes('rel="canonical"')) {
    out = out.replace(
      "</head>",
      `    <link rel="canonical" href="${site}/" />\n  </head>`,
    );
  }
  return out;
}

export function robotsTxt(site) {
  return `User-agent: *\nAllow: /\n\nSitemap: ${site}/sitemap.xml\n`;
}

export function sitemapXml(site, lastmod) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>${site}/</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
`;
}

export function seoArtifacts(siteUrl) {
  const site = (siteUrl || "http://localhost:5174").replace(/\/+$/, "");
  const dist = fileURLToPath(new URL("../dist", import.meta.url));
  return {
    name: "seo-artifacts",
    apply: "build",
    closeBundle() {
      const htmlPath = path.join(dist, "index.html");
      writeFileSync(htmlPath, absolutiseHtml(readFileSync(htmlPath, "utf8"), site));
      writeFileSync(path.join(dist, "robots.txt"), robotsTxt(site));
      const lastmod = new Date().toISOString().slice(0, 10);
      writeFileSync(path.join(dist, "sitemap.xml"), sitemapXml(site, lastmod));
    },
  };
}
