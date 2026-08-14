import { api, bytesToGB, escapeHtml } from "../api-client.js";

class PartitionsView extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <div class="view-header">
        <h1>Disk Management</h1>
        <div class="view-actions">
          <fluent-button id="refresh-btn" appearance="outline">
            <svg width="14" height="14" slot="start"><use href="#icon-refresh"/></svg>
            Refresh
          </fluent-button>
        </div>
      </div>
      <div id="disks"><div class="empty-state">Loading partition layout&hellip;</div></div>
    `;
    this.querySelector("#refresh-btn").addEventListener("click", () => this._load());
    this._load();
  }

  async _load() {
    const container = this.querySelector("#disks");
    container.innerHTML = `<div class="empty-state">Loading partition layout&hellip;</div>`;
    try {
      const disks = await api.partitions();
      this._render(disks);
    } catch (err) {
      container.innerHTML = `<div class="empty-state">Could not load partitions: ${escapeHtml(err.message)}</div>`;
    }
  }

  _render(disks) {
    const container = this.querySelector("#disks");
    if (!disks.length) {
      container.innerHTML = `<div class="empty-state">No disks detected.</div>`;
      return;
    }

    container.innerHTML = disks
      .map((disk) => {
        const segments = disk.segments
          .map((seg) => {
            const flex = Math.max(seg.size / disk.size, 0.02);
            if (seg.unallocated) {
              return `<div class="partition-segment unallocated" style="flex:${flex}">Unallocated<br>${bytesToGB(seg.size)} GB</div>`;
            }
            return `<div class="partition-segment" style="flex:${flex}">${escapeHtml(seg.letter)}<br>${bytesToGB(seg.size)} GB</div>`;
          })
          .join("");

        const rows = disk.segments
          .filter((s) => !s.unallocated)
          .map(
            (s) => `
              <tr>
                <td>${escapeHtml(s.letter)}</td>
                <td>${s.primary ? "Primary" : "Logical"}</td>
                <td>${escapeHtml(s.filesystem || "Unknown")}</td>
                <td>${bytesToGB(s.size)} GB</td>
                <td>${s.percent_used}%</td>
              </tr>`
          )
          .join("");

        return `
          <div class="disk-block card">
            <div class="disk-block-header">
              <h3>Disk ${escapeHtml(disk.disk_number)} &mdash; ${escapeHtml(disk.model)}</h3>
              <span>${bytesToGB(disk.size)} GB total &middot; ${bytesToGB(disk.unallocated)} GB unallocated</span>
            </div>
            <div class="partition-track">${segments}</div>
            <table class="partition-table">
              <thead><tr><th>Partition</th><th>Type</th><th>File System</th><th>Capacity</th><th>% Used</th></tr></thead>
              <tbody>${rows || '<tr><td colspan="5">No mounted partitions.</td></tr>'}</tbody>
            </table>
          </div>`;
      })
      .join("");
  }
}

customElements.define("partitions-view", PartitionsView);
