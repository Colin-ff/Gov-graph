# GovGraph frontend (React + Vite dev server).
# Serves the SPA on :5173 with hot reload. The browser calls the backend
# directly on the host-published port (see src/api/client.ts default), so no
# build-time API URL is required.
FROM node:22-bookworm-slim

WORKDIR /app

# Install dependencies first for layer caching. `npm install` (not `npm ci`)
# resolves the correct platform-specific optional deps (e.g. rollup's Linux
# binary) even though package-lock.json was generated on another OS.
COPY package.json package-lock.json ./
RUN npm install

COPY . .

EXPOSE 5173

# --host binds Vite to 0.0.0.0 so the dev server is reachable from the host.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
