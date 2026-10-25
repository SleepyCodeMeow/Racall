import type { NextConfig } from 'next';
// Optional local build limit for machines where VM/model workloads are unstable.
const buildCpus = Number(process.env.RACALL_BUILD_CPUS);
const config: NextConfig = {
  output: 'export',
  images: { unoptimized: true },
  poweredByHeader: false,
  ...(Number.isInteger(buildCpus) && buildCpus >= 1 && buildCpus <= 32
    ? { experimental: { cpus: buildCpus } }
    : {}),
};
export default config;
