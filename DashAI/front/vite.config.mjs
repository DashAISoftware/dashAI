import react from "@vitejs/plugin-react";
import { defineConfig, transformWithEsbuild } from "vite";

const jsxInJs = {
  name: "treat-js-as-jsx",
  async transform(code, id) {
    if (!/src\/.*\.js$/.test(id.replace(/\\/g, "/"))) {
      return null;
    }
    return transformWithEsbuild(code, id, {
      loader: "jsx",
      jsx: "automatic",
    });
  },
};

export default defineConfig({
  plugins: [jsxInJs, react()],
  server: {
    port: 3000,
  },
  build: {
    outDir: "build",
    sourcemap: false,
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        ".js": "jsx",
      },
    },
  },
});
