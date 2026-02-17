/** @type {import('next').NextConfig} */
const backendUrl = process.env.NMM_BACKEND_URL || "http://backend:8080";

const nextConfig = {
  assetPrefix: process.env.NODE_ENV === "production" ? "/admin" : "",

  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
      { source: "/static/:path*", destination: `${backendUrl}/static/:path*` },
    ];
  },
};

export default nextConfig;

