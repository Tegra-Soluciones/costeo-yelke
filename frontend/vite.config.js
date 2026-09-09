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
        // TODO con hash -- incluida la entrada. Los chunks lazy hacen
        // `import "./index-<hash>.js"`, así que si la entrada NO llevara hash el
        // navegador serviría una copia vieja cacheada y se cargarían dos versiones
        // de la app a la vez. El controlador www lee el index.html generado para
        // saber qué archivos referenciar (ver www/costeo_yelke.py).
        entryFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
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
