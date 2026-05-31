# ---- deps ----
FROM node:22-alpine AS deps
WORKDIR /app
# Optional registry mirror — set NPM_REGISTRY in .env if npmjs.org is slow/blocked
# from your server (e.g. https://registry.npmmirror.com).
ARG NPM_REGISTRY=https://registry.npmjs.org/
# Force IPv4 first: a broken/slow IPv6 path to the registry is the usual cause of
# npm hanging for minutes then dying with "Exit handler never called". Plus generous
# retries/timeouts for flaky links.
ENV NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NODE_OPTIONS=--dns-result-order=ipv4first \
    NPM_CONFIG_FETCH_RETRIES=5 \
    NPM_CONFIG_FETCH_RETRY_MAXTIMEOUT=180000 \
    NPM_CONFIG_FETCH_TIMEOUT=600000
COPY package.json package-lock.json* ./
RUN npm config set registry "$NPM_REGISTRY" && npm ci --no-audit --no-fund

# ---- build ----
FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Cap Node heap so the Next build stays within small-VPS memory (relies on swap).
ENV NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS=--max-old-space-size=1024
RUN npm run build

# ---- runtime (standalone) ----
FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
RUN addgroup -g 1001 nodejs && adduser -u 1001 -G nodejs -S nextjs
COPY --from=build /app/public ./public
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
