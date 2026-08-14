import { api, bytesToGB, levelFor, escapeHtml } from "../api-client.js";
import { ws } from "../ws.js";

class DriveView extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <div class="view-header">
        <h1>Drive Information</h1>
        <div class="view-actions">
          <div id="live-indicator" data-state="connecting"><span class="dot"></span><span class="label">Live</span></div>
        </div>
      </div>
      <div class="card-grid" id="drive-cards"><div class="empty-state">Loading drives&hellip;</div></div>
    `;

    this._indicator = this.querySelector("#live-indicator");
    this._onOpen = () => this._setLive("live");
    this._onClose = () => this._setLive("disconnected");
    this._onTick = (event) => this._render(event.detail.drives);

    ws.addEventListener("open", this._onOpen);
    ws.addEventListener("close", this._onClose);
    ws.addEventListener("tick", this._onTick);

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

        return `
          <div class="card">
            <p class="card-title"><svg width="16" height="16"><use href="#icon-drive"/></svg> ${escapeHtml(drive.model)}</p>
            <p class="card-subtitle">${escapeHtml(drive.interface)} &middot; ${escapeHtml(drive.media_type)} &middot; ${bytesToGB(drive.size)} GB</p>
            ${partitions || '<p class="card-subtitle">No mounted partitions.</p>'}
          </div>`;
      })
      .join("");
  }
}

customElements.define("drive-view", DriveView);
