import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker
  output: 'standalone',

  // API rewrites for development (only if API URL is defined)
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

    // Only add rewrites if API URL is explicitly set (for local development)
    if (apiUrl && apiUrl !== 'undefined') {
      return [
        {
          source: '/api/:path*',
          destination: `${apiUrl}/api/:path*`,
        },
      ];
    }

    // In Docker/production, no rewrites needed (direct network communication)
    return [];
  },
};

export default nextConfig;
