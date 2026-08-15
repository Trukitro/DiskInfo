// Wrapper delgado sobre fetch() para /api/* -- mismo origen que el backend
// (FastAPI sirve frontend/ como estaticos), así que no hace falta CORS.

const API_BASE = "/api";

async function request(path, options = {}) {
  // fetch() defaults an unset Content-Type to text/plain for a string
  // body, which makes FastAPI treat the whole body as a raw string
  // instead of parsing it as JSON -- explicit here rather than relying on
  // the browser's default, for every request that actually has a body.
  const headers = options.body ? { "Content-Type": "application/json", ...options.headers } : options.headers;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* respuesta sin JSON, se mantiene res.statusText */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  appInfo: () => request("/app-info"),
  drives: () => request("/drives"),
  health: () => request("/health"),
  partitions: () => request("/partitions"),
  startBenchmark: (letter, totalMb) => request(`/benchmark/${letter}?total_mb=${totalMb}`, { method: "POST" }),
  benchmarkHistory: (letter) => request(`/benchmark/history?drive=${letter}`),
  healthHistory: (deviceId) => request(`/health/history?device_id=${encodeURIComponent(deviceId)}`),
  settings: () => request("/settings"),
  updateSettings: (patch) => request("/settings", { method: "PUT", body: JSON.stringify(patch) }),
};

export function bytesToGB(bytes) {
  return (bytes / 1024 ** 3).toFixed(2);
}

export function levelFor(percent) {
  if (percent >= 90) return "danger";
  if (percent >= 75) return "warn";
  return "good";
}

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
