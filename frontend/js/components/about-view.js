import { api } from "../api-client.js";

const FEATURES = [
  ["icon-drive", "Drive Info", "View basic information about all connected drives, including capacity and usage."],
  ["icon-health", "Health Status", "Monitor drive health using SMART data and predict potential failures."],
  ["icon-partitions", "Partitions", "Examine detailed partition information in a Windows Disk Management-style interface."],
  ["icon-benchmark", "Benchmark", "Test drive read and write speeds with a built-in, live-updating benchmarking tool."],
];

class AboutView extends HTMLElement {
  async connectedCallback() {
    let version = "";
    try {
      version = (await api.appInfo()).version;
    } catch {
      /* offline dev preview without a running backend */
    }

    this.innerHTML = `
      <div class="view-header"><h1>About DiskInfo</h1></div>
      <div class="card" style="margin-bottom: var(--space-4)">
        <p class="card-subtitle" style="font-size:13px">Version ${version}</p>
        <p style="font-size:13px;color:var(--text-secondary);max-width:640px">
          DiskInfo is a comprehensive disk management and monitoring tool that provides
          detailed information about your storage devices, helping you monitor disk
          health, performance, and usage.
        </p>
      </div>
      <div class="card-grid" style="margin-bottom: var(--space-4)">
        ${FEATURES.map(
          ([icon, title, desc]) => `
          <div class="card">
            <p class="card-title"><svg width="16" height="16"><use href="#${icon}"/></svg> ${title}</p>
            <p class="card-subtitle">${desc}</p>
          </div>`
        ).join("")}
      </div>
      <div class="card">
        <p class="card-title">Creator</p>
        <p class="card-subtitle">Created by EtchTechnologies (Rikion)</p>
        <a href="https://github.com/Trukitro" data-external-ok style="color:var(--accent);font-size:13px">github.com/Trukitro</a>
      </div>
    `;
  }
}

customElements.define("about-view", AboutView);
