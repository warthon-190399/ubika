import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, /api se redirige a la API Express (node server.js, puerto 3001)
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": { target: "http://localhost:3001", changeOrigin: true } } },
});
