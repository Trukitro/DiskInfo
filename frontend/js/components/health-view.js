import { api, escapeHtml } from "../api-client.js";
import { ws } from "../ws.js";

class HealthView extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <div class="view-header">
        <h1>Drive Health Status</h1>
        <div class="view-actions">
          <fluent-button id="refresh-btn" appearance="outline">
            <svg width="14" height="14" slot="start"><use href="#icon-refresh"/></svg>
            Refresh
          </fluent-button>
        </div>
      </div>
      <div class="card-grid" id="health-cards"><div class="empty-state">Loading health data&hellip;</div></div>
    `;

    this.querySelector("#refresh-btn").addEventListener("click", () => this._load());
    this._onTick = (event) => this._render(event.detail.health);
    ws.addEventListener("tick", this._onTick);

    this._load();
  }

  disconnectedCallback() {
    ws.removeEventListener("tick", this._onTick);
  }

  async _load() {
    try {
      const health = await api.health();
      this._render(health);
    } catch (err) {
      this.querySelector("#health-cards").innerHTML = `<div class="empty-state">Could not load health data: ${escapeHtml(err.message)}</div>`;
    }
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
        return `
          <div class="card">
            <p class="card-title">
              <svg width="16" height="16"><use href="#icon-health"/></svg> ${escapeHtml(entry.model)}
              <span class="badge ${badgeClass}" style="margin-left:auto">${badgeText}</span>
            </p>
            <p class="card-subtitle">${escapeHtml(entry.reason)}</p>
            <div class="progress-track"><div class="progress-fill" data-level="${level}" style="width:${entry.health_percentage}%"></div></div>
          </div>`;
      })
      .join("");
  }
}

customElements.define("health-view", HealthView);
