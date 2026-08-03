import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig({
  plugins: [vue()],
  base: "/assets/costeo_yelke/costeo-app/",
  build: {
    outDir: path.resolve(__dirname, "../costeo_yelke/public/costeo-app"),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // Entrada principal sin hash → referencia estable desde el HTML de Frappe
        entryFileNames: "assets/index.js",
        assetFileNames: (info) =>
          info.name?.endsWith(".css") ? "assets/index.css" : "assets/[name]-[hash][extname]",
        // Chunks dinámicos (páginas lazy) sí llevan hash
        chunkFileNames: "assets/[name]-[hash].js",
      },
    },
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    proxy: {
      "/api":    "http://sandbox.local:8000",
      "/assets": "http://sandbox.local:8000",
    },
  },
});
