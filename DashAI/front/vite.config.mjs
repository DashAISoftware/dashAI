import react from "@vitejs/plugin-react";
import { defineConfig, transformWithEsbuild } from "vite";

const jsxInJs = {
  name: "treat-js-as-jsx",
  async transform(code, id) {
    const file = id.replace(/\\/g, "/").split("?")[0];
    if (file.includes("/node_modules/") || !/\/src\/.*\.js$/.test(file)) {
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
