import type { NextConfig } from "next";

// Rewrites are resolved at build time: the Docker build receives BACKEND_URL as an arg.
const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/backend/:path*", destination: `${backendUrl}/:path*` }];
  },
};

export default nextConfig;
