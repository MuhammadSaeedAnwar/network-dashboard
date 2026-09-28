import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Reads the backend base URL from an env var at build/dev time so the
// frontend never hardcodes localhost -- see .env.example at the repo root.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
});
