import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dashboardRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig = {
  output: 'export',
  assetPrefix: process.env.NEXT_PUBLIC_DASHBOARD_ASSET_PREFIX ?? '/dashboard',
  turbopack: {
    root: dashboardRoot
  },
  images: {
    unoptimized: true
  }
};

export default nextConfig;
