import { PHASE_DEVELOPMENT_SERVER } from "next/constants.js";

// `npm run build:static` sets NEXT_STATIC_EXPORT=1 to produce a plain static site in
// `out/`. Regular `dev`, `build` and `start` (used by Railway) never set it.
const isStaticExport = process.env.NEXT_STATIC_EXPORT === "1";

/** @type {(phase: string) => import('next').NextConfig} */
export default function nextConfig(phase) {
  const isDevServer = phase === PHASE_DEVELOPMENT_SERVER;
  return {
    reactStrictMode: true,
    // Development-only pages use the `.dev.tsx` extension (for example the local API
    // health check). They exist under `next dev` only and are never part of a
    // production build or static export.
    pageExtensions: isDevServer ? ["dev.tsx", "tsx", "ts", "jsx", "js"] : ["tsx", "ts", "jsx", "js"],
    ...(isStaticExport
      ? {
          output: "export",
          // A static host has no image optimizer; serve images as-is.
          images: { unoptimized: true },
        }
      : {}),
  };
}
