import {
  provideFluentDesignSystem,
  fluentButton,
  fluentCard,
  fluentSelect,
  fluentOption,
  fluentDivider,
  fluentSwitch,
  fluentTextField,
  accentBaseColor,
  baseLayerLuminance,
  StandardLuminance,
  SwatchRGB,
} from "../vendor/fluent-web-components.min.js";
import "./nav-guard.js";
import { applyTheme, getTheme, isEffectivelyDark } from "./theme.js";
import { api } from "./api-client.js";
import "./ws.js";

import "./components/dashboard-view.js";
import "./components/drive-view.js";
import "./components/health-view.js";
import "./components/partitions-view.js";
import "./components/benchmark-view.js";
import "./components/settings-view.js";
import "./components/about-view.js";

provideFluentDesignSystem().register(
  fluentButton(),
  fluentCard(),
  fluentSelect(),
  fluentOption(),
  fluentDivider(),
  fluentSwitch(),
  fluentTextField()
);

// DiskInfo's own teal, not PulseGuard's blue -- Fluent components pick up
// this accent for the same controls (buttons, selects) our hand-rolled CSS
// tokens already use it for.
accentBaseColor.setValueFor(document.body, SwatchRGB.create(0x14 / 255, 0xb8 / 255, 0xa6 / 255));

function syncFluentLuminance(isDark) {
  baseLayerLuminance.setValueFor(document.body, isDark ? StandardLuminance.DarkMode : StandardLuminance.LightMode);
}

document.addEventListener("theme-change", (event) => syncFluentLuminance(event.detail.isDark));

applyTheme(getTheme());
syncFluentLuminance(isEffectivelyDark());
document.getElementById("theme-toggle").addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-theme-choice]");
  if (btn) applyTheme(btn.dataset.themeChoice);
});

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "icon-dashboard", tag: "dashboard-view" },
  { id: "drives", label: "Drive Info", icon: "icon-drive", tag: "drive-view" },
  { id: "health", label: "Health Status", icon: "icon-health", tag: "health-view" },
  { id: "partitions", label: "Partitions", icon: "icon-partitions", tag: "partitions-view" },
  { id: "benchmark", label: "Benchmark", icon: "icon-benchmark", tag: "benchmark-view" },
  { id: "settings", label: "Settings", icon: "icon-settings", tag: "settings-view" },
  { id: "about", label: "About", icon: "icon-info", tag: "about-view" },
];

const navList = document.getElementById("nav-list");
const viewRoot = document.getElementById("view-root");

navList.innerHTML = NAV_ITEMS.map(
  (item) => `
  <li class="nav-item" data-nav-id="${item.id}" tabindex="0" role="link" aria-label="${item.label}">
    <svg class="nav-icon" width="16" height="16"><use href="#${item.icon}"/></svg>
    <span>${item.label}</span>
  </li>`
).join("");

function renderView(id) {
  const item = NAV_ITEMS.find((n) => n.id === id) || NAV_ITEMS[0];
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.navId === item.id);
  });
  viewRoot.innerHTML = "";
  viewRoot.appendChild(document.createElement(item.tag));
  window.location.hash = `#/${item.id}`;
}

navList.addEventListener("click", (event) => {
  const li = event.target.closest(".nav-item");
  if (li) renderView(li.dataset.navId);
});

navList.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const li = event.target.closest(".nav-item");
  if (!li) return;
  event.preventDefault();
  renderView(li.dataset.navId);
});

window.addEventListener("hashchange", () => {
  const id = window.location.hash.replace("#/", "");
  if (id) renderView(id);
});

renderView(window.location.hash.replace("#/", "") || "dashboard");

const versionEl = document.getElementById("app-version");
api
  .appInfo()
  .then((info) => (versionEl.textContent = `${info.name} ${info.version}`))
  .catch(() => {});
