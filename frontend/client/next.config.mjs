const backendUrl = process.env.NMM_BACKEND_URL || "http://backend:8080";

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
      { source: "/static/:path*", destination: `${backendUrl}/static/:path*` },
    ];
  },
};

export default nextConfig;
