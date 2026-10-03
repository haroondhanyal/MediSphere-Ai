import type { NextConfig } from "next";
import { resolve } from "node:path";

const nextConfig: NextConfig = { output: "standalone", outputFileTracingRoot: resolve(process.cwd()), devIndicators: false };
export default nextConfig;
