/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async rewrites() {
    // Proxy API calls to the backend so the browser stays same-origin.
    const api = process.env.API_INTERNAL_URL || "http://api:8000";
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};

export default nextConfig;
