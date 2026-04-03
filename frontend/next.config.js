/** @type {import('next').NextConfig} */
const nextConfig = {
  // All data fetching is client-side against the FastAPI backend
  reactStrictMode: true,

  // Allow images from localhost (for future receipt previews)
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
      },
    ],
  },

  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

module.exports = nextConfig;
