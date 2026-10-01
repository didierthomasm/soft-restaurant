import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: { tsconfigPaths: true },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/lib/**/*.ts", "src/proxy.ts"],
      exclude: ["src/lib/api/schema.d.ts", "src/lib/api/attendance.ts", "src/lib/api/config.ts", "src/lib/api/reviews.ts"],
      thresholds: { lines: 80, functions: 80, branches: 80 },
    },
  },
});
