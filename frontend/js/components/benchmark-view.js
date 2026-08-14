import { api, escapeHtml } from "../api-client.js";
import { ws, getLastTick } from "../ws.js";

const WRITE_COLOR = "#14b8a6";
const READ_COLOR = "#818cf8";
const BUSY_THRESHOLD_BPS = 5 * 1024 * 1024; // 5 MB/s sustained read or write

const SIZE_PRESETS = [
  { label: "Quick -- 50MB", value: 50 },
  { label: "Standard -- 200MB", value: 200 },
  { label: "Thorough -- 1000MB", value: 1000 },
];

class BenchmarkView extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <div class="view-header">
        <h1>Disk Benchmark</h1>
      </div>
      <div class="benchmark-controls">
        <fluent-select id="drive-select" style="min-width: 90px"></fluent-select>
        <fluent-select id="size-select" style="min-width: 170px">
          ${SIZE_PRESETS.map(
            (p) => `<fluent-option value="${p.value}"${p.value === 200 ? " selected" : ""}>${p.label}</fluent-option>`
          ).join("")}
        </fluent-select>
        <fluent-button id="run-btn" appearance="accent">Run Benchmark</fluent-button>
        <span id="status-label" class="card-subtitle" style="margin:0"></span>
      </div>
      <div id="busy-warning" class="card-subtitle" style="display:none;color:var(--warn);margin-top:calc(var(--space-3) * -1)"></div>
      <div class="benchmark-results">
        <div class="benchmark-stat"><div class="value" id="write-avg">&ndash;</div><div class="label">Write MB/s</div></div>
        <div class="benchmark-stat"><div class="value" id="read-avg">&ndash;</div><div class="label">Read MB/s</div></div>
      </div>
      <div class="card" style="margin-bottom: var(--space-4)">
        <div class="chart-wrap"><canvas id="benchmark-canvas"></canvas></div>
      </div>
      <div class="card">
        <p class="card-title">Recent runs</p>
        <table class="partition-table" id="history-table">
          <thead><tr><th>Date</th><th>Write MB/s</th><th>Read MB/s</th><th>Size</th><th>Cache bypassed</th></tr></thead>
          <tbody><tr><td colspan="5">No runs yet.</td></tr></tbody>
        </table>
      </div>
    `;

    this._select = this.querySelector("#drive-select");
    this._sizeSelect = this.querySelector("#size-select");
    this._runBtn = this.querySelector("#run-btn");
    this._statusLabel = this.querySelector("#status-label");
    this._busyWarning = this.querySelector("#busy-warning");
    this._writeAvg = this.querySelector("#write-avg");
    this._readAvg = this.querySelector("#read-avg");
    this._historyBody = this.querySelector("#history-table tbody");
    this._driveByLetter = new Map();
    this._activeDrive = null;

    this._runBtn.addEventListener("click", () => this._runBenchmark());
    this._select.addEventListener("change", () => this._loadHistory());
    this._onProgress = (event) => this._handleProgress(event.detail);
    ws.addEventListener("benchmark_progress", this._onProgress);

    this._initChart();
    this._loadDrives();
  }

  disconnectedCallback() {
    ws.removeEventListener("benchmark_progress", this._onProgress);
    this._chart?.destroy();
  }

  _initChart() {
    const ctx = this.querySelector("#benchmark-canvas").getContext("2d");
    this._chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          { label: "Write MB/s", data: [], borderColor: WRITE_COLOR, backgroundColor: WRITE_COLOR, tension: 0.25, pointRadius: 0 },
          { label: "Read MB/s", data: [], borderColor: READ_COLOR, backgroundColor: READ_COLOR, tension: 0.25, pointRadius: 0 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: { y: { beginAtZero: true } },
      },
    });
  }

  async _loadDrives() {
    try {
      const drives = await api.drives();
      this._driveByLetter.clear();
      drives.forEach((d) => d.partitions.forEach((p) => this._driveByLetter.set(p.mountpoint.replace(/[:\\]/g, ""), d.device_id)));
      const letters = [...this._driveByLetter.keys()];
      this._select.innerHTML = letters.map((l) => `<fluent-option value="${l}">${escapeHtml(l)}:</fluent-option>`).join("");
      if (!letters.length) {
        this._runBtn.disabled = true;
        this._statusLabel.textContent = "No drives available for benchmarking.";
      } else {
        this._loadHistory();
      }
    } catch (err) {
      this._statusLabel.textContent = `Could not load drives: ${err.message}`;
    }
  }

  async _loadHistory() {
    const letter = this._select.value;
    if (!letter) return;
    try {
      const rows = await api.benchmarkHistory(letter);
      this._renderHistory(rows);
    } catch {
      /* history is a nice-to-have, don't block the view on it failing */
    }
  }

  _renderHistory(rows) {
    if (!rows.length) {
      this._historyBody.innerHTML = `<tr><td colspan="5">No runs yet.</td></tr>`;
      return;
    }
    this._historyBody.innerHTML = rows
      .map(
        (r) => `
        <tr>
          <td>${new Date(r.ts * 1000).toLocaleString()}</td>
          <td>${r.write_avg_mb_s}</td>
          <td>${r.read_avg_mb_s}</td>
          <td>${r.total_mb} MB</td>
          <td>${r.cache_bypassed ? "Yes" : "No"}</td>
        </tr>`
      )
      .join("");
  }

  async _runBenchmark() {
    const letter = this._select.value;
    if (!letter) return;

    const deviceId = this._driveByLetter.get(letter);
    const activity = deviceId ? getLastTick()?.io_activity?.[deviceId] : null;
    if (activity && (activity.read_bps > BUSY_THRESHOLD_BPS || activity.write_bps > BUSY_THRESHOLD_BPS)) {
      this._busyWarning.style.display = "block";
      this._busyWarning.textContent = "This drive has active I/O right now -- results may be skewed.";
    } else {
      this._busyWarning.style.display = "none";
    }

    this._activeDrive = letter;
    this._runBtn.disabled = true;
    this._statusLabel.textContent = `Running benchmark on ${letter}:…`;
    this._writeAvg.textContent = "–";
    this._readAvg.textContent = "–";
    this._chart.data.labels = [];
    this._chart.data.datasets[0].data = [];
    this._chart.data.datasets[1].data = [];
    this._chart.update();

    try {
      await api.startBenchmark(letter, Number(this._sizeSelect.value) || 200);
    } catch (err) {
      this._statusLabel.textContent = `Benchmark failed to start: ${err.message}`;
      this._runBtn.disabled = false;
    }
  }

  _handleProgress(data) {
    if (data.drive !== this._activeDrive) return;

    if (data.phase === "write" || data.phase === "read") {
      const datasetIndex = data.phase === "write" ? 0 : 1;
      if (this._chart.data.labels.length < data.of) {
        this._chart.data.labels = Array.from({ length: data.of }, (_, i) => `${(i + 1) * 10}MB`);
      }
      this._chart.data.datasets[datasetIndex].data[data.chunk - 1] = data.speed_mb_s;
      this._chart.update();
      this._statusLabel.textContent = `${data.phase === "write" ? "Writing" : "Reading"}… (${data.chunk}/${data.of})`;
    } else if (data.phase === "fallback") {
      this._statusLabel.textContent = `Note: ${data.message}`;
    } else if (data.phase === "done") {
      this._writeAvg.textContent = data.write_avg_mb_s;
      this._readAvg.textContent = data.read_avg_mb_s;
      this._statusLabel.textContent = data.cache_bypassed
        ? "Done -- measured against the physical drive (cache bypassed)."
        : "Done -- fell back to buffered I/O; read speed may be cache-inflated.";
      this._runBtn.disabled = false;
      this._activeDrive = null;
      this._loadHistory();
    } else if (data.phase === "error") {
      this._statusLabel.textContent = `Benchmark failed: ${data.message}`;
      this._runBtn.disabled = false;
      this._activeDrive = null;
    }
  }
}

customElements.define("benchmark-view", BenchmarkView);
