# Deploying the landing page to InfinityFree

InfinityFree serves static files with Apache. It cannot run Node.js or Python, so it
can host only the **public landing page** and its browser-based illustrative demo. The
demo uses simulated data and makes no model or API calls. The FastAPI backend, the
database, and any real assessment workflow need separate hosting later.

## 1. Generate the static export

From `apps/web`, with Node.js 20 or later:

```powershell
npm ci
npm run build:static
```

`build:static` runs `next build` in static-export mode (`NEXT_STATIC_EXPORT=1`, see
`apps/web/next.config.mjs`) and writes plain HTML, CSS, JavaScript, fonts, and images to
`apps/web/out/`. It also adds an `.htaccess` file that uses `404.html` for unknown paths,
and it fails if the export references `localhost` or a development-only page.

Regular `npm run dev`, `npm run build`, and `npm run start` are unchanged. The local API
health check (`/api-health`, file `app/api-health/page.dev.tsx`) is available there but
is intentionally left out of the static export.

## 2. Set the final site URL, then rebuild

Social networks need absolute image URLs. Set `NEXT_PUBLIC_SITE_URL` to the public
origin of the site before building. Without it, the site works normally but the
Open Graph and Twitter image tags are omitted, so link previews have no image.

PowerShell:

```powershell
$env:NEXT_PUBLIC_SITE_URL = "https://your-domain.example"
npm run build:static
```

Command Prompt:

```bat
set NEXT_PUBLIC_SITE_URL=https://your-domain.example
npm run build:static
```

Use the exact address visitors will open, including `https://` if the site has an SSL
certificate. The build rejects `localhost` values.

## 3. Upload to InfinityFree

1. Open the hosting account's file manager or connect with an FTP client such as
   FileZilla.
2. Open the domain's `htdocs` folder. Remove the default placeholder page (for example
   `index2.html`) if present.
3. Upload the **contents** of `apps/web/out/`, not the `out` folder itself. After
   uploading, `htdocs/index.html` must exist directly inside `htdocs`.
4. Upload every folder and file, including `_next/` (scripts, styles, and fonts),
   `brand/`, `icon.png`, `apple-icon.png`, `404.html`, `index.txt`, and `.htaccess`.
   Some FTP clients hide files whose names start with a dot; make sure `.htaccess` is
   uploaded.
5. Open the site and hard-refresh the browser.

If you use a prepared ZIP of the export, its root already contains `index.html`.
Extract it so that the files land directly in `htdocs`, or extract it on your computer
and upload the extracted contents.

## What will not work

- Uploading the raw Next.js source (`app/`, `components/`, `package.json`, and so on).
  The host cannot build or run it.
- Uploading only the `.next/` folder. It is build cache for a Node.js server, not a
  website.
- Uploading `out/` without `_next/`. The page loads without styles or the demo.

## Updating the site

Rebuild with `npm run build:static`, then replace the files in `htdocs` with the new
contents of `out/`. File names under `_next/static/` change between builds, so remove
the old `_next` folder before uploading the new one.
