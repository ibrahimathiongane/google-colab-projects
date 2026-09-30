# Build the static bundle, then serve it with nginx (which also
# reverse-proxies /api to the gateway). No dev server in production.
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine

# Outside /etc/nginx/conf.d on purpose: the stock config globs *.conf there.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx-headers.conf /etc/nginx/security-headers.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
