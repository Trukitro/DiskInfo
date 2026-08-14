// Singleton WS connection shared across views -- created once when app.js
// loads and kept alive across navigation, so switching views never drops a
// benchmark run in progress or re-triggers the reconnect backoff.

import { WsClient } from "./ws-client.js";

export const ws = new WsClient();

// Caches the most recent "tick" payload so a view that just mounted (e.g.
// Benchmark, checking current I/O activity before starting a run) can read
// current state immediately instead of waiting for the next broadcast.
let lastTick = null;
ws.addEventListener("tick", (event) => {
  lastTick = event.detail;
});

export function getLastTick() {
  return lastTick;
}
