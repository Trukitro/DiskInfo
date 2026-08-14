import { api, escapeHtml } from "../api-client.js";
import { ws } from "../ws.js";

const WRITE_COLOR = "#14b8a6";
const READ_COLOR = "#818cf8";

class BenchmarkView extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <div class="view-header">
        <h1>Disk Benchmark</h1>
      </div>
      <div class="benchmark-controls">
        <fluent-select id="drive-select" style="min-width: 140px"></fluent-select>
        <fluent-button id="run-btn" appearance="accent">Run Benchmark</fluent-button>
        <span id="status-label" class="card-subtitle" style="margin:0"></span>
      </div>
      <div class="benchmark-results">
        <div class="benchmark-stat"><div class="value" id="write-avg">&ndash;</div><div class="label">Write MB/s</div></div>
        <div class="benchmark-stat"><div class="value" id="read-avg">&ndash;</div><div class="label">Read MB/s</div></div>
      </div>
      <div class="card">
        <div class="chart-wrap"><canvas id="benchmark-canvas"></canvas></div>
      </div>
    `;

    this._select = this.querySelector("#drive-select");
    this._runBtn = this.querySelector("#run-btn");
    this._statusLabel = this.querySelector("#status-label");
    this._writeAvg = this.querySelector("#write-avg");
    this._readAvg = this.querySelector("#read-avg");
    this._activeDrive = null;

    this._runBtn.addEventListener("click", () => this._runBenchmark());
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
      const letters = [...new Set(drives.flatMap((d) => d.partitions.map((p) => p.mountpoint.replace(/[:\\]/g, ""))))];
      this._select.innerHTML = letters.map((l) => `<fluent-option value="${l}">${escapeHtml(l)}:</fluent-option>`).join("");
      if (!letters.length) {
        this._runBtn.disabled = true;
        this._statusLabel.textContent = "No drives available for benchmarking.";
      }
    } catch (err) {
      this._statusLabel.textContent = `Could not load drives: ${err.message}`;
    }
  }

  async _runBenchmark() {
    const letter = this._select.value;
    if (!letter) return;

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
      await api.startBenchmark(letter);
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
    } else if (data.phase === "done") {
      this._writeAvg.textContent = data.write_avg_mb_s;
      this._readAvg.textContent = data.read_avg_mb_s;
      this._statusLabel.textContent = "Done.";
      this._runBtn.disabled = false;
      this._activeDrive = null;
    } else if (data.phase === "error") {
      this._statusLabel.textContent = `Benchmark failed: ${data.message}`;
      this._runBtn.disabled = false;
      this._activeDrive = null;
    }
  }
}

customElements.define("benchmark-view", BenchmarkView);
