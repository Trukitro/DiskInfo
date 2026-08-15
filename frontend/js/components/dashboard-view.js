import { api, bytesToGB, escapeHtml, levelFor } from "../api-client.js";
import { ws } from "../ws.js";

class DashboardView extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <div class="view-header"><h1>Dashboard</h1></div>
      <div class="card-grid" id="dashboard-cards"><div class="empty-state">Loading&hellip;</div></div>
    `;

    // Benchmark history is fetched once per drive on load and cached, not
    // re-fetched on every 5s WS tick -- it only changes after the user
    // runs a benchmark, which this summary view doesn't itself trigger.
    this._perfByLetter = new Map();
    this._onTick = (event) => this._render(event.detail.drives, event.detail.health);
    ws.addEventListener("tick", this._onTick);

    this._load();
  }

  disconnectedCallback() {
    ws.removeEventListener("tick", this._onTick);
  }

  async _load() {
    try {
      const [drives, health] = await Promise.all([api.drives(), api.health()]);
      await this._loadPerf(drives);
      this._render(drives, health);
    } catch (err) {
      this.querySelector("#dashboard-cards").innerHTML = `<div class="empty-state">Could not load dashboard: ${escapeHtml(err.message)}</div>`;
    }
  }

  async _loadPerf(drives) {
    const letters = [...new Set(drives.flatMap((d) => d.partitions.map((p) => p.mountpoint.replace(/[:\\]/g, ""))))];
    await Promise.all(
      letters.map(async (letter) => {
        try {
          const runs = await api.benchmarkHistory(letter);
          this._perfByLetter.set(letter, runs[0] || null);
        } catch {
          this._perfByLetter.set(letter, null);
        }
      })
    );
  }

  _render(drives, health) {
    const container = this.querySelector("#dashboard-cards");
    if (!container) return;

    if (!drives.length) {
      container.innerHTML = `<div class="empty-state">No drives detected.</div>`;
      return;
    }

    const healthByDevice = new Map(health.map((h) => [h.device_id, h]));

    container.innerHTML = drives
      .map((drive) => {
        const h = healthByDevice.get(drive.device_id);
        const letters = drive.partitions.map((p) => p.mountpoint.replace(/[:\\]/g, ""));
        const lastRun = letters.map((l) => this._perfByLetter.get(l)).find((r) => r);

        let perfBadge = "";
        if (lastRun?.underperforming) {
          perfBadge = `<span class="badge warn" title="${escapeHtml(lastRun.underperforming_reason || "")}">Underperforming</span>`;
        } else if (lastRun) {
          perfBadge = `<span class="badge good">Perf OK</span>`;
        }

        const maxPercent = drive.partitions.length ? Math.max(...drive.partitions.map((p) => p.percent)) : 0;
        const spaceLevel = levelFor(maxPercent);
        const healthBadgeClass = h?.predicted_failure ? "danger" : "good";
        const healthBadgeText = h?.predicted_failure ? "Warning" : "Healthy";
        const temp = h?.temperature_c != null ? `${h.temperature_c}&deg;C` : "--";
        const bootBadge = drive.is_boot ? `<span class="badge info">Boot</span>` : "";

        return `
          <div class="card">
            <p class="card-title">
              <svg width="16" height="16"><use href="#icon-drive"/></svg> ${escapeHtml(drive.model)}${bootBadge}
            </p>
            <p class="card-subtitle">${escapeHtml(drive.bus_type)} &middot; ${escapeHtml(drive.media_type)} &middot; ${bytesToGB(drive.size)} GB &middot; ${temp}</p>
            <div class="progress-track"><div class="progress-fill" data-level="${spaceLevel}" style="width:${maxPercent}%"></div></div>
            <div class="card-row" style="padding-top:var(--space-3);padding-bottom:0;gap:6px;justify-content:flex-start">
              <span class="badge ${healthBadgeClass}">${healthBadgeText}</span>
              ${perfBadge}
            </div>
          </div>`;
      })
      .join("");
  }
}

customElements.define("dashboard-view", DashboardView);
