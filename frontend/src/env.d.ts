/**
 * Runtime environment configuration injected via env.js at deploy time.
 * Augments the Window interface so we don't need `(window as any)` casts.
 */
interface RuntimeEnv {
  API_URL?: string;
}

interface Window {
  __env?: RuntimeEnv;
}
