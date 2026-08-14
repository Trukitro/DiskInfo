// Selector de tema (claro / oscuro / sistema) -- aplicado al cargar en
// app.js, antes de que exista ninguna vista, y accionado desde los botones
// del sidebar en index.html.

const STORAGE_KEY = "diskinfo-theme";
const media = window.matchMedia("(prefers-color-scheme: dark)");

export function getTheme() {
  return localStorage.getItem(STORAGE_KEY) || "system";
}

export function isEffectivelyDark(choice = getTheme()) {
  return choice === "dark" || (choice === "system" && media.matches);
}

export function applyTheme(choice) {
  if (choice === "system") {
    document.documentElement.removeAttribute("data-theme");
  } else {
    document.documentElement.setAttribute("data-theme", choice);
  }
  localStorage.setItem(STORAGE_KEY, choice);
  document.querySelectorAll("#theme-toggle button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.themeChoice === choice);
  });
  document.dispatchEvent(new CustomEvent("theme-change", { detail: { isDark: isEffectivelyDark(choice) } }));
}

// Only matters while "system" is the active choice -- an explicit
// light/dark pick shouldn't silently flip if the OS theme changes underneath it.
media.addEventListener("change", () => {
  if (getTheme() === "system") applyTheme("system");
});
