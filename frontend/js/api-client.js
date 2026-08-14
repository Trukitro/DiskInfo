// Wrapper delgado sobre fetch() para /api/* -- mismo origen que el backend
// (FastAPI sirve frontend/ como estaticos), así que no hace falta CORS.

const API_BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
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
  startBenchmark: (letter) => request(`/benchmark/${letter}`, { method: "POST" }),
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
