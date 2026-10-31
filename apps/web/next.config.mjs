// `npm run build:static` sets NEXT_STATIC_EXPORT=1 to produce a plain static site in
// `out/` for hosts without a Node.js server. Regular `dev`, `build` and `start` are unchanged.
const isStaticExport = process.env.NEXT_STATIC_EXPORT === "1";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Development-only pages use the `.dev.tsx` extension (for example the local API
  // health check) and are left out of the static export.
  pageExtensions: isStaticExport ? ["tsx", "ts", "jsx", "js"] : ["dev.tsx", "tsx", "ts", "jsx", "js"],
  ...(isStaticExport
    ? {
        output: "export",
        // A static host has no image optimizer; serve images as-is.
        images: { unoptimized: true },
      }
    : {}),
};

export default nextConfig;
