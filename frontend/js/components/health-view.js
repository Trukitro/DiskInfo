import { api, escapeHtml } from "../api-client.js";
import { ws } from "../ws.js";

const TEMP_COLOR = "#fbbf24";

class HealthView extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <div class="view-header">
        <h1>Drive Health Status</h1>
        <div class="view-actions">
          <fluent-button id="export-btn" appearance="outline">Export</fluent-button>
          <fluent-button id="refresh-btn" appearance="outline">
            <svg width="14" height="14" slot="start"><use href="#icon-refresh"/></svg>
            Refresh
          </fluent-button>
        </div>
      </div>
      <div class="card-grid" id="health-cards"><div class="empty-state">Loading health data&hellip;</div></div>
      <div class="card" id="history-panel" style="display:none;margin-top:var(--space-4)">
        <p class="card-title">
          Temperature History -- <span id="history-panel-title"></span>
          <fluent-button id="close-history-btn" appearance="stealth" style="margin-left:auto">Close</fluent-button>
        </p>
        <div class="chart-wrap" id="history-chart-wrap" style="height:180px"><canvas id="health-history-canvas"></canvas></div>
      </div>
    `;

    // One shared Chart.js instance for whichever device's history panel is
    // open, rather than one instance per card -- panel lives outside the
    // card grid specifically so it survives _render()'s full-innerHTML
    // rebuild on every WS tick.
    this._chart = null;
    this._openDeviceId = null;
    this._historyPanel = this.querySelector("#history-panel");
    this._historyTitle = this.querySelector("#history-panel-title");

    this.querySelector("#refresh-btn").addEventListener("click", () => this._load());
    this.querySelector("#export-btn").addEventListener("click", () => {
      window.open("/api/export?view=health&format=csv", "_blank");
    });
    this.querySelector("#close-history-btn").addEventListener("click", () => this._closeHistory());
    this.querySelector("#health-cards").addEventListener("click", (event) => {
      const btn = event.target.closest(".history-btn");
      if (btn) this._openHistory(btn.dataset.deviceId, btn.dataset.model);
    });

    this._onTick = (event) => this._render(event.detail.health);
    ws.addEventListener("tick", this._onTick);

    this._load();
  }

  disconnectedCallback() {
    ws.removeEventListener("tick", this._onTick);
    this._chart?.destroy();
  }

  async _load() {
    try {
      const health = await api.health();
      this._render(health);
    } catch (err) {
      this.querySelector("#health-cards").innerHTML = `<div class="empty-state">Could not load health data: ${escapeHtml(err.message)}</div>`;
    }
  }

  async _openHistory(deviceId, model) {
    this._openDeviceId = deviceId;
    this._historyModel = model;
    this._historyTitle.textContent = model;
    this._historyPanel.style.display = "block";
    try {
      const rows = await api.healthHistory(deviceId);
      this._renderChart(rows);
    } catch {
      /* history is a nice-to-have, leave the panel showing the last chart rather than erroring */
    }
  }

  _closeHistory() {
    this._openDeviceId = null;
    this._historyPanel.style.display = "none";
  }

  _renderChart(rows) {
    const labels = rows.map((r) => new Date(r.ts * 1000).toLocaleTimeString());
    const temps = rows.map((r) => r.temperature_c);

    if (!this._chart) {
      const ctx = this.querySelector("#health-history-canvas").getContext("2d");
      this._chart = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [{ label: "Temperature (°C)", data: temps, borderColor: TEMP_COLOR, backgroundColor: TEMP_COLOR, tension: 0.25, pointRadius: 0, spanGaps: true }],
        },
        options: { responsive: true, maintainAspectRatio: false, animation: false, scales: { y: { beginAtZero: false } } },
      });
    } else {
      this._chart.data.labels = labels;
      this._chart.data.datasets[0].data = temps;
      this._chart.update();
    }

    // Recomputed from the base model name each time (not appended) --
    // _renderChart re-runs on every WS tick while the panel is open, and
    // appending would duplicate this suffix on every refresh.
    this._historyTitle.textContent =
      this._historyModel + (temps.every((t) => t == null) ? " (no temperature data recorded for this drive yet)" : "");
  }

  _render(entries) {
    const container = this.querySelector("#health-cards");
    if (!container) return;

    if (!entries.length) {
      container.innerHTML = `<div class="empty-state">No drives detected.</div>`;
      return;
    }

    container.innerHTML = entries
      .map((entry) => {
        const badgeClass = entry.predicted_failure ? "danger" : "good";
        const badgeText = entry.predicted_failure ? "Warning" : "Healthy";
        const level = entry.predicted_failure ? "danger" : "good";
        const temp = entry.temperature_c != null ? `${entry.temperature_c}&deg;C` : "--";
        const tbw = entry.tbw_estimate_gb != null ? `${entry.tbw_estimate_gb} GB written (est.)` : null;
        const attrRows = (entry.smart_attributes || [])
          .map((a) => `<tr><td>${a.id}</td><td>${a.current}</td><td>${a.worst}</td><td>${a.raw}</td></tr>`)
          .join("");

        return `
          <div class="card">
            <p class="card-title">
              <svg width="16" height="16"><use href="#icon-health"/></svg> ${escapeHtml(entry.model)}
              <span class="badge ${badgeClass}" style="margin-left:auto">${badgeText}</span>
            </p>
            <p class="card-subtitle">${escapeHtml(entry.reason)} &middot; ${temp}${tbw ? ` &middot; ${tbw}` : ""}</p>
            <div class="progress-track"><div class="progress-fill" data-level="${level}" style="width:${entry.health_percentage}%"></div></div>
            <fluent-button class="history-btn" appearance="stealth" data-device-id="${escapeHtml(entry.device_id)}" data-model="${escapeHtml(entry.model)}" style="margin-top:var(--space-2)">History</fluent-button>
            ${
              attrRows
                ? `<details style="margin-top:var(--space-2)">
                    <summary class="card-subtitle" style="cursor:pointer;margin-bottom:0">Raw SMART attributes (advanced)</summary>
                    <table class="partition-table">
                      <thead><tr><th>ID</th><th>Current</th><th>Worst</th><th>Raw</th></tr></thead>
                      <tbody>${attrRows}</tbody>
                    </table>
                  </details>`
                : ""
            }
          </div>`;
      })
      .join("");

    // Keep the open history panel's chart in sync with the latest tick
    // instead of only updating on the initial click.
    if (this._openDeviceId) {
      const match = entries.find((e) => e.device_id === this._openDeviceId);
      if (match) api.healthHistory(this._openDeviceId).then((rows) => this._renderChart(rows)).catch(() => {});
    }
  }
}

customElements.define("health-view", HealthView);
