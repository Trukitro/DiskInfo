import { api, bytesToGB, levelFor, escapeHtml } from "../api-client.js";
import { ws } from "../ws.js";

const SPARKLINE_SAMPLES = 30;
const SPARKLINE_WIDTH = 120;
const SPARKLINE_HEIGHT = 28;

function formatBps(bps) {
  if (!bps) return "0 B/s";
  if (bps >= 1024 ** 2) return `${(bps / 1024 ** 2).toFixed(1)} MB/s`;
  if (bps >= 1024) return `${(bps / 1024).toFixed(1)} KB/s`;
  return `${bps.toFixed(0)} B/s`;
}

function sparklinePoints(values, max, width, height) {
  if (!values.length) return "";
  const step = width / Math.max(values.length - 1, 1);
  return values.map((v, i) => `${(i * step).toFixed(1)},${(height - (v / max) * height).toFixed(1)}`).join(" ");
}

function renderSparkline(hist) {
  const read = hist?.read || [];
  const write = hist?.write || [];
  if (!read.length && !write.length) return "";
  const max = Math.max(1, ...read, ...write);
  const readPts = sparklinePoints(read, max, SPARKLINE_WIDTH, SPARKLINE_HEIGHT);
  const writePts = sparklinePoints(write, max, SPARKLINE_WIDTH, SPARKLINE_HEIGHT);
  return `
    <svg class="io-sparkline" viewBox="0 0 ${SPARKLINE_WIDTH} ${SPARKLINE_HEIGHT}" width="${SPARKLINE_WIDTH}" height="${SPARKLINE_HEIGHT}" preserveAspectRatio="none">
      <polyline points="${writePts}" fill="none" stroke="#818cf8" stroke-width="1.5" />
      <polyline points="${readPts}" fill="none" stroke="#14b8a6" stroke-width="1.5" />
    </svg>`;
}

class DriveView extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <div class="view-header">
        <h1>Drive Information</h1>
        <div class="view-actions">
          <fluent-button id="export-btn" appearance="outline">Export</fluent-button>
          <div id="live-indicator" data-state="connecting"><span class="dot"></span><span class="label">Live</span></div>
        </div>
      </div>
      <div class="card-grid" id="drive-cards"><div class="empty-state">Loading drives&hellip;</div></div>
    `;

    this._indicator = this.querySelector("#live-indicator");
    this._activityHistory = new Map();
    this._lastDrives = [];
    this._onOpen = () => this._setLive("live");
    this._onClose = () => this._setLive("disconnected");
    this._onTick = (event) => {
      this._updateActivityHistory(event.detail.io_activity || {});
      this._render(event.detail.drives);
    };

    ws.addEventListener("open", this._onOpen);
    ws.addEventListener("close", this._onClose);
    ws.addEventListener("tick", this._onTick);
    this.querySelector("#export-btn").addEventListener("click", () => {
      window.open("/api/export?view=drives&format=csv", "_blank");
    });

    this._load();
  }

  disconnectedCallback() {
    ws.removeEventListener("open", this._onOpen);
    ws.removeEventListener("close", this._onClose);
    ws.removeEventListener("tick", this._onTick);
  }

  _setLive(state) {
    this._indicator.dataset.state = state;
    this._indicator.querySelector(".label").textContent =
      state === "live" ? "Live" : state === "disconnected" ? "Disconnected" : "Connecting";
  }

  _updateActivityHistory(ioActivity) {
    for (const [deviceId, activity] of Object.entries(ioActivity)) {
      if (!this._activityHistory.has(deviceId)) {
        this._activityHistory.set(deviceId, { read: [], write: [] });
      }
      const hist = this._activityHistory.get(deviceId);
      hist.read.push(activity.read_bps);
      hist.write.push(activity.write_bps);
      if (hist.read.length > SPARKLINE_SAMPLES) hist.read.shift();
      if (hist.write.length > SPARKLINE_SAMPLES) hist.write.shift();
      hist.current = activity;
    }
  }

  async _load() {
    try {
      const drives = await api.drives();
      this._render(drives);
    } catch (err) {
      this.querySelector("#drive-cards").innerHTML = `<div class="empty-state">Could not load drive info: ${escapeHtml(err.message)}</div>`;
    }
  }

  _render(drives) {
    const container = this.querySelector("#drive-cards");
    if (!container) return;
    this._lastDrives = drives;

    if (!drives.length) {
      container.innerHTML = `<div class="empty-state">No drives detected.</div>`;
      return;
    }

    container.innerHTML = drives
      .map((drive) => {
        const partitions = drive.partitions
          .map((part) => {
            const level = levelFor(part.percent);
            return `
              <div class="card-row" style="flex-direction: column; align-items: stretch; gap: 4px; padding: var(--space-2) 0;">
                <div class="card-row" style="padding: 0;">
                  <span>${escapeHtml(part.mountpoint)}</span>
                  <strong>${bytesToGB(part.used)} / ${bytesToGB(part.total)} GB (${part.percent.toFixed(0)}%)</strong>
                </div>
                <div class="progress-track"><div class="progress-fill" data-level="${level}" style="width:${part.percent}%"></div></div>
              </div>`;
          })
          .join("");

        const hist = this._activityHistory.get(drive.device_id);
        const activityLine = hist?.current
          ? `<div class="card-row" style="padding:0"><span>R ${formatBps(hist.current.read_bps)} &middot; W ${formatBps(hist.current.write_bps)}</span></div>`
          : "";
        const sparkline = renderSparkline(hist);

        const bootBadge = drive.is_boot ? `<span class="badge info" style="margin-left:auto">Boot</span>` : "";

        return `
          <div class="card">
            <p class="card-title"><svg width="16" height="16"><use href="#icon-drive"/></svg> ${escapeHtml(drive.model)}${bootBadge}</p>
            <p class="card-subtitle">${escapeHtml(drive.bus_type)} &middot; ${escapeHtml(drive.media_type)} &middot; ${bytesToGB(drive.size)} GB</p>
            ${sparkline ? `<div style="margin-bottom:var(--space-2)">${sparkline}${activityLine}</div>` : ""}
            ${partitions || '<p class="card-subtitle">No mounted partitions.</p>'}
          </div>`;
      })
      .join("");
  }
}

customElements.define("drive-view", DriveView);
