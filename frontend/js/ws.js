// Singleton WS connection shared across views -- created once when app.js
// loads and kept alive across navigation, so switching views never drops a
// benchmark run in progress or re-triggers the reconnect backoff.

import { WsClient } from "./ws-client.js";

export const ws = new WsClient();
