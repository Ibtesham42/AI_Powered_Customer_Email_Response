/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Absolute origin of the backend API for a separate-origin production deploy
   * (e.g. "https://api.example.com"), no trailing slash. Unset in dev — the
   * Vite proxy serves the API same-origin, so requests stay relative.
   */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
