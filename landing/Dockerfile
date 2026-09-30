# The landing imports the app's design tokens (../frontend/src/tokens.css),
# so the build context is the repo root — see docker-compose.yml.
FROM node:20-alpine AS build

WORKDIR /repo
COPY landing/package*.json landing/
RUN npm ci --prefix landing
COPY landing/ landing/
COPY frontend/src/tokens.css frontend/src/tokens.css

# Where the "Open app" CTAs point in production.
ARG VITE_APP_URL=http://localhost:5173
ENV VITE_APP_URL=$VITE_APP_URL

# Canonical site URL — og:*, canonical, robots.txt and sitemap.xml.
ARG VITE_SITE_URL=http://localhost:5174
ENV VITE_SITE_URL=$VITE_SITE_URL

# Optional privacy-friendly analytics (Plausible-compatible, no cookies).
ARG VITE_ANALYTICS_SRC=
ENV VITE_ANALYTICS_SRC=$VITE_ANALYTICS_SRC
ARG VITE_ANALYTICS_DOMAIN=
ENV VITE_ANALYTICS_DOMAIN=$VITE_ANALYTICS_DOMAIN

RUN npm --prefix landing run build

FROM nginx:1.27-alpine

# Outside /etc/nginx/conf.d on purpose: the stock config globs *.conf there.
COPY landing/nginx.conf /etc/nginx/conf.d/default.conf
# Same security-header file as the frontend container (single source).
COPY frontend/nginx-headers.conf /etc/nginx/security-headers.conf
COPY --from=build /repo/landing/dist /usr/share/nginx/html

EXPOSE 80
