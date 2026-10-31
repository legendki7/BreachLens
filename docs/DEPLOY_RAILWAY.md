# Deploying the landing page to Railway

Railway runs the public BreachLens landing page and its browser-based illustrative demo
with the normal Next.js production server (`next build` + `next start`). Only the
frontend in `apps/web` is deployed. The demo uses simulated data and makes no model or
API calls. The FastAPI backend, PostgreSQL, and model integrations are not part of this
service and need separate hosting later.

## Service settings

Create a service from the GitHub repository and enter:

| Setting | Value |
| --- | --- |
| Repository | `legendki7/BreachLens` |
| Branch | `feat/breachlens-landing` |
| Root Directory | `/apps/web` |
| Builder | Railpack (default) |
| Build command | Leave empty. Railpack installs dependencies and runs `npm run build` (`next build`). |
| Start command | Leave empty. `apps/web/railpack.json` sets `node node_modules/next/dist/bin/next start --hostname 0.0.0.0`. |
| Watch Paths (optional) | `/apps/web/**`, so backend-only commits do not redeploy the site |
| Healthcheck Path (optional) | `/` |

`apps/web` has its own `package.json` and `package-lock.json` and no workspace
dependencies, so it builds on its own as the root directory.

The start command runs Node directly instead of `npm run start`, so Railway's stop
signal reaches the Next.js server. The server listens on `0.0.0.0` and takes its port
from the `PORT` variable that Railway provides; no port is hard-coded.

## Variables

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_SITE_URL` | `https://<your Railway public domain>` once the domain exists (see below). |
| `NEXT_TELEMETRY_DISABLED` | `1` (optional) |

Do not set:

- `PORT`. Railway injects it.
- `NEXT_STATIC_EXPORT`. It switches the build to static-export mode for file-only hosts,
  and `next start` cannot serve that output.

## Public domain and sharing URLs

`NEXT_PUBLIC_SITE_URL` is read at build time to produce the canonical link and absolute
Open Graph and Twitter image URLs. Without it the site works, but those tags are
omitted.

1. Deploy once, then open the service's **Settings → Networking** and choose
   **Generate Domain** (or add a custom domain). If Railway asks for a port, use the one
   shown in the deploy logs on the `Network: http://0.0.0.0:<port>` line.
2. Copy the full domain and set `NEXT_PUBLIC_SITE_URL` to it with `https://`, for
   example `https://<name>.up.railway.app`.
3. Redeploy. The value is baked in during the build, so changing it requires a new
   build.
4. Check the page source for `<link rel="canonical"` and `og:image` with your domain.

## Local check of the production server

From `apps/web`:

```powershell
npm ci
npm run build
$env:PORT = "4173"; node node_modules/next/dist/bin/next start --hostname 0.0.0.0
```

Then open `http://localhost:4173`.

## Notes

- The local API health check (`/api-health`, file `app/api-health/page.dev.tsx`) exists
  only under `npm run dev` and is not part of production builds.
- The optional static export for file-only hosts is still available through
  `npm run build:static` (see [InfinityFree deployment](DEPLOY_INFINITYFREE.md)). It does
  not affect the Railway build.
