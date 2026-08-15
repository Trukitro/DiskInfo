import { api, escapeHtml } from "../api-client.js";

class SettingsView extends HTMLElement {
  async connectedCallback() {
    this.innerHTML = `
      <div class="view-header"><h1>Settings</h1></div>
      <div class="card" style="max-width: 480px">
        <div class="settings-row">
          <label for="poll-interval">Refresh interval (seconds)</label>
          <fluent-text-field id="poll-interval" type="number"></fluent-text-field>
        </div>
        <div class="settings-row">
          <label for="low-space">Low space warning (%)</label>
          <fluent-text-field id="low-space" type="number"></fluent-text-field>
        </div>
        <div class="settings-row">
          <label for="temp-alert">Temperature alert (&deg;C, blank to disable)</label>
          <fluent-text-field id="temp-alert" type="number" placeholder="off"></fluent-text-field>
        </div>
        <div class="settings-row">
          <label for="notifications">Notifications</label>
          <fluent-switch id="notifications"></fluent-switch>
        </div>
        <div class="settings-row">
          <label for="autostart">Start with Windows</label>
          <fluent-switch id="autostart"></fluent-switch>
        </div>
        <fluent-divider></fluent-divider>
        <div class="settings-row">
          <label for="port">Server port</label>
          <fluent-text-field id="port" type="number"></fluent-text-field>
        </div>
        <p class="card-subtitle">Port changes take effect after restarting DiskInfo.</p>
        <div style="display:flex;align-items:center;gap:var(--space-3);margin-top:var(--space-3)">
          <fluent-button id="save-btn" appearance="accent">Save</fluent-button>
          <span id="status-label" class="card-subtitle" style="margin:0"></span>
        </div>
      </div>
    `;

    this._pollInterval = this.querySelector("#poll-interval");
    this._lowSpace = this.querySelector("#low-space");
    this._tempAlert = this.querySelector("#temp-alert");
    this._notifications = this.querySelector("#notifications");
    this._autostart = this.querySelector("#autostart");
    this._port = this.querySelector("#port");
    this._status = this.querySelector("#status-label");

    this.querySelector("#save-btn").addEventListener("click", () => this._save());

    try {
      const settings = await api.settings();
      this._pollInterval.value = settings.poll_interval_s;
      this._lowSpace.value = settings.low_space_pct;
      this._tempAlert.value = settings.temperature_alert_c ?? "";
      this._notifications.checked = settings.notifications_enabled;
      this._autostart.checked = settings.autostart;
      this._port.value = settings.port;
    } catch (err) {
      this._status.textContent = `Could not load settings: ${escapeHtml(err.message)}`;
    }
  }

  async _save() {
    this._status.textContent = "Saving…";
    try {
      const tempAlertRaw = this._tempAlert.value.trim();
      const patch = {
        poll_interval_s: Number(this._pollInterval.value),
        low_space_pct: Number(this._lowSpace.value),
        temperature_alert_c: tempAlertRaw === "" ? null : Number(tempAlertRaw),
        notifications_enabled: this._notifications.checked,
        autostart: this._autostart.checked,
        port: Number(this._port.value),
      };
      await api.updateSettings(patch);
      this._status.textContent = "Saved.";
    } catch (err) {
      this._status.textContent = `Could not save: ${escapeHtml(err.message)}`;
    }
  }
}

customElements.define("settings-view", SettingsView);
