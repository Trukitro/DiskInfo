# DiskInfo -- Roadmap Completo / Feature Backlog

Documento vivo con todas las mejoras posibles discutidas, organizadas por
categoría y prioridad. Sirve como referencia para ir sacando features
individuales y convertirlas en planes de implementación propios (estilo
`diskinfo-space-viz-plan.md`).

**Propósito original del proyecto**: detectar SSD/HDD/M.2, mostrar
velocidades reales de cada disco, y dar información que ayude a manejar
discos en una PC/servidor Windows -- no es un clon genérico de
CrystalDiskInfo, es una herramienta de gestión.

## Cómo usar este documento

- **P0**: núcleo del propósito original, alta prioridad
- **P1**: mejora significativa, complementa el núcleo
- **P2**: nice-to-have, valor pero no urgente
- **Fuera de scope**: confirmado explícitamente fuera (ver
  `DiskInfo-project-plan.md`)

`[x]` = confirmado para la próxima release. `[~]` = confirmado pero de baja
confianza/experimental, no debe bloquear el release. `[ ]` = todavía sin
decidir, queda en el backlog.

Cuando se decida trabajar una feature, se saca de acá y se arma un plan
propio (estilo `diskinfo-space-viz-plan.md`) con contexto para Claude Code.

---

## Release 6.1.0 -- shipped 2026-08-14

Los 10 ítems propuestos por Claude Code, con dos ajustes acordados en la
revisión: la Settings UI (#3) se construye como el módulo de config
centralizada (ver sección 11), y se suma infraestructura de testing (#11,
de la sección 8) para que cada módulo nuevo o reescrito nazca con tests en
vez de agregarlos después. Ver `CHANGELOG.md` [6.1.0] para el detalle
completo de cada ítem.

1. ✅ Fix de exactitud del benchmark (`FILE_FLAG_NO_BUFFERING`, I/O alineado a sector) -- verificado contra hardware real: el mismo HDD que reportaba >3000 MB/s ahora reporta ~100 MB/s
2. ✅ Detección real de tipo de disco/bus vía `MSFT_PhysicalDisk` -- verificado: un disco de este mismo proyecto pasó de "Fixed hard disk media" a "NVMe SSD" correctamente
3. ✅ Settings UI + módulo de config centralizada
4. ✅ Toggle de autostart editable desde la app -- verificado escribiendo/leyendo el registro directamente
5. ✅ Tamaño de benchmark configurable en la UI
6. ✅ Historial de benchmarks (almacenamiento local + tabla de tendencia)
7. ✅ Actividad de I/O en vivo por disco (+ aviso antes de benchmarkear si el disco está ocupado)
8. ✅ Temperatura de disco -- experimental/P2; en el hardware de prueba de este proyecto el driver no expone el atributo SMART, así que se ve "--" (comportamiento esperado, no un bug)
9. ✅ Infraestructura de testing (pytest, 20 tests) -- un test detectó y ayudó a corregir un bug real en el path de lectura sin buffer antes de tocar hardware real
10. ✅ Export simple CSV/JSON de los datos ya mostrados en pantalla
11. ⏳ Screenshots reales del README -- **no se pudo completar**: no hay forma de guardar a disco las capturas del panel de navegador con las herramientas disponibles en esta sesión. Sigue pendiente.

De la sección 1 y 2 (núcleo del propósito), lo que no esté marcado ✅ arriba
queda para la siguiente release.

---

## Release 6.2.0 -- shipped 2026-08-14

Bug report real del usuario (benchmark fallando con `Permission denied` en
`C:`) llevó a la decisión de que DiskInfo corra siempre elevado, y de ahí
se continuó con 14 ítems del backlog: el resto del núcleo P0 (secciones 1
y 2), profundidad de salud (sección 3), un Dashboard que conecta todo
(sección 11), y robustez continuada (sección 8). El treemap (sección 5)
se dejó afuera a propósito -- su plan nunca se compartió con esta sesión.
Ver `CHANGELOG.md` [6.2.0] para el detalle completo.

- ✅ **Fix de elevación** (no estaba en la lista original, salió del bug
  report): la app pide UAC en cada inicio; autostart migrado de la
  registry Run key a un Scheduled Task (`/rl highest`), ya que Windows no
  arranca de forma confiable un exe con manifest de elevación desde Run.
- ✅ Disco de arranque marcado (Drive Info, Dashboard).
- ✅ Benchmark de IOPS/latencia (4K random) sumado al throughput secuencial.
- ✅ Detección de discos "underperforming" vs. su categoría esperada.
- ⏳ Generación PCIe / controlador-chipset -- **investigado, no
  implementado**: `Win32_SCSIControllerDevice` no resuelve de forma
  confiable en el hardware real de este proyecto, y los controladores que
  sí enumera Windows solo dan nombres genéricos ("Standard NVM Express
  Controller"), no el chipset real. No vale la pena mostrar "Unknown"
  siempre.
- ✅ Historial de temperatura/salud en el tiempo (gráfico).
- ✅ Umbral de alerta de temperatura configurable en Settings.
- ✅ Tabla de atributos SMART crudos + estimado de TBW, para usuarios
  avanzados (ambos con fallback honesto a "no disponible", igual que
  temperatura).
- ✅ Dashboard/Overview unificado como vista de entrada por defecto.
- ✅ Tests de integración de WebSocket (FastAPI `TestClient`).
- ✅ Logging a archivo (`diskinfo.log`, rotativo).
- ✅ Linting (`ruff`) + CI (`.github/workflows/ci.yml`).
- 🐛 **Bug encontrado y corregido durante la verificación de esta misma
  release**: el botón "Save" de Settings fallaba silenciosamente (422) --
  `api-client.js` nunca mandaba `Content-Type: application/json` en los
  PUT. Nunca se había probado el flujo completo por UI en 6.1.0, solo por
  API directa.

**Pendiente real de 6.2.0**: screenshots del README (bloqueado desde
6.1.0, sigue igual). Generación PCIe/chipset quedan fuera por decisión
informada, no por falta de tiempo -- ver arriba.

---

## 1. Identificación y clasificación de discos (P0 -- núcleo)

- [x] ✅ Shipped en 6.1.0: reemplazada la detección por string del nombre
  del modelo por `MSFT_PhysicalDisk` (WMI `root\Microsoft\Windows\Storage`),
  que expone `MediaType`, `SpindleSpeed` y `BusType` reales -- misma fuente
  que usa Windows Settings y `Get-PhysicalDisk`.
- [x] ✅ Shipped en 6.1.0 (parte) / investigado en 6.2.0: SATA vs NVMe ya
  se detecta via `BusType`. Generación PCIe (Gen3/4/5) investigada en
  6.2.0 y **no implementada** -- no hay fuente WMI confiable, requeriría
  `DeviceIoControl` de bajo nivel sin hardware multi-vendor para validar.
- [ ] Mostrar controlador/chipset al que está conectado cada disco --
  investigado en 6.2.0 y **no implementado**: `Win32_SCSIControllerDevice`
  no resuelve de forma confiable en el hardware de prueba, y los nombres
  que da Windows son genéricos, no el chipset real.
- [x] ✅ Shipped en 6.2.0: disco de arranque marcado (`is_boot`, comparado
  contra `os.environ["SystemDrive"]`), badge en Drive Info y Dashboard.
- [x] ✅ Shipped en 6.2.0: columna "Physical Disk" agregada a la tabla de
  Partitions -- el dato ya existía en la estructura, era un gap de UI.

## 2. Rendimiento y velocidad (P0 -- núcleo)

- [x] ✅ Shipped en 6.1.0: el benchmark ya no mide contra el page cache de
  Windows -- usa `FILE_FLAG_NO_BUFFERING` con I/O alineado a sector vía
  `win32file`/`mmap` para bypassear el cache y medir el disco de verdad.
- [x] ✅ Shipped en 6.1.0: parámetros `total_mb` expuestos en la UI como
  presets (Quick/Standard/Thorough).
- [x] ✅ Shipped en 6.2.0: test de IOPS/latencia (4K random write+read)
  sumado al throughput secuencial -- verificado contra hardware real
  (HDD): 622 write IOPS/1.6ms, 76 read IOPS/13ms, ambos plausibles para
  un 7200RPM.
- [x] ✅ Shipped en 6.1.0: historial de benchmarks (disco, fecha, promedio
  lectura/escritura) guardado local (SQLite), con tabla de tendencia bajo
  el gráfico.
- [ ] Benchmark programado (ej. semanal, opcional)
- [x] ✅ Shipped en 6.2.0: detección de discos "underperforming" vs su
  categoría esperada (`expectations.py`, umbrales por media_type/bus_type),
  con badge de advertencia y guardado en el historial.
- [x] ✅ Shipped en 6.1.0: actividad de I/O real en vivo por disco vía
  `psutil.disk_io_counters(perdisk=True)`, transmitida por el WebSocket
  existente, mostrada como sparkline en la card de cada disco.

## 3. Salud y estado (P0/P1)

- [x] ✅ Shipped en 6.2.0: historial de temperatura/salud en el tiempo,
  gráfico Chart.js on-demand por disco (botón "History"), snapshots
  guardados cada 60s en `health_snapshots`.
- [x] ✅ Shipped en 6.2.0 (parte): umbral de alerta de temperatura
  configurable en Settings. % de vida restante queda para más adelante
  (ningún disco de prueba expone un atributo SMART equivalente).
- [x] ✅ Shipped en 6.2.0: tabla de atributos SMART crudos (id/current/
  worst/raw) en un `<details>` colapsable por disco, para usuarios avanzados.
- [x] ✅ Shipped en 6.2.0: estimado de TBW (atributo SMART 241 x 512 bytes),
  mismo fallback honesto a "no disponible" que temperatura.
- [ ] Detección de discos recién conectados (USB) en vivo sin refrescar manualmente
- [~] ✅ Shipped en 6.1.0 (experimental): temperatura de disco donde esté
  disponible, parseando los atributos SMART crudos 194/190 de
  `MSStorageDriver_ATAPISmartData`. En el hardware de prueba de este
  proyecto el driver no expuso el atributo en ningún disco -- se muestra
  "--", que es el comportamiento esperado (no un bug), confirmando que la
  degradación a "no disponible" funciona en la práctica.

## 4. Gestión práctica SSD/HDD (P1)

- [ ] TRIM status (activado/desactivado) por SSD, con acción de un click
  para activarlo vía `fsutil`
- [ ] Modo de energía del disco (APM/AAM en SATA; power states en NVMe)
- [ ] Cola de comandos: NCQ (SATA) / número de queues (NVMe)
- [ ] Espacio reservado / over-provisioning del SSD, si el driver lo expone
- [ ] Firmware del disco + verificación de actualización disponible
  (ambicioso, depende del fabricante -- investigar factibilidad antes de
  comprometer)

## 5. Visualización de espacio (P1 -- ya con plan propio)

- [ ] Treemap de uso de disco estilo WinDirStat (plan ya armado:
  `diskinfo-space-viz-plan.md` -- pendiente de compartir con esta sesión)
- [ ] Detección dinámica de instalaciones Windows por disco (multi-disco/multi-SO en servidores)
- [ ] Agrupación de archivos de sistema en nodo colapsado, toggle para mostrarlos
- [ ] v2 del treemap: color por tipo de extensión de archivo

## 6. Partitions (P1/P2, expande lo ya existente)

- [ ] Indicador visual de fragmentación (solo lectura -- no hay defrag
  activo, resize está out of scope)
- [ ] Detalle de tipo de partición (GPT type GUID: EFI, Recovery, MSR, datos)

## 7. UX / calidad de vida (P1)

- [x] ✅ Shipped en 6.1.0: página de Settings en la UI, editando el mismo
  `settings.py` centralizado (poll interval, % de espacio bajo,
  notificaciones, autostart, puerto).
- [x] ✅ Shipped en 6.1.0, mecanismo reemplazado en 6.2.0: toggle de
  autostart editable desde la app. Migrado de la registry Run key a un
  Scheduled Task (`/rl highest`) en 6.2.0, como consecuencia de la
  decisión de correr siempre elevado -- ver sección 8 y
  `DiskInfo-project-plan.md`.
- [ ] Atajo de teclado global para abrir/mostrar la ventana
- [ ] Resumen compacto al hacer hover sobre el ícono de bandeja
- [ ] Auto-actualización de la app (check for updates, dado que el
  instalador no está firmado)
- [ ] Persistencia de preferencias de usuario (toggles, último disco
  seleccionado, tema) en un archivo de config -- ver Settings arriba,
  debería vivir en el mismo lugar

## 8. Robustez técnica / calidad de código (P0 -- transversal, no es "feature" pero es lo que hace la app robusta)

- [x] ✅ Shipped en 6.1.0: pytest agregado para backend (20 tests) cubriendo
  drives/health/settings/history/benchmark. Pagó por sí solo de inmediato:
  un test detectó un bug real en el path de lectura sin buffer (reuso
  incorrecto del buffer entre llamadas a `ReadFile`) antes de que llegara
  a ejecutarse contra un disco real. Cobertura retroactiva del resto de
  módulos queda para ir sumando con el tiempo.
- [x] ✅ Shipped en 6.2.0: tests de integración de WebSocket (FastAPI
  `TestClient`: tick recibido, reconexión, conexiones concurrentes).
- [ ] Manejo consistente de errores: WMI no disponible, disco desconectado
  a mitad de operación, permisos insuficientes -- definir un formato de
  error uniforme entre todos los módulos, no ad-hoc por feature
- [x] ✅ Shipped en 6.2.0: logging a archivo rotativo
  (`%LOCALAPPDATA%\DiskInfo\diskinfo.log`), reemplaza los `print()` que no
  iban a ningún lado en la app empaquetada. README actualizado para pedirlo
  en issues.
- [ ] Manejo de reconexión de WebSocket en el frontend si el backend se
  reinicia o hay hiccup (parcialmente cubierto: `ws-client.js` ya
  reconecta con backoff, falta UX explícita en cada vista)
- [x] ✅ Shipped en 6.2.0: `ruff` configurado (`backend/ruff.toml`) y
  agregado a un nuevo workflow de CI (`.github/workflows/ci.yml`, separado
  del `release.yml` existente) que corre lint + pytest en cada push/PR.
- [x] ✅ Shipped en 6.2.0 (resuelto distinto a como estaba planteado): en
  vez de "elevar solo cuando haga falta", la decisión final -- pedida
  explícitamente por el usuario tras un bug report real -- fue elevar
  siempre, una sola vez, de forma predecible. Ver "Why DiskInfo runs
  elevated" en `DiskInfo-project-plan.md`.

## 9. Empaquetado y distribución (P2)

- [ ] Firmar el instalador (resuelve el warning de SmartScreen documentado
  en Troubleshooting)
- [ ] Versión portable (sin instalador, un solo .exe) además del
  instalador actual
- [ ] Changelog automatizado a partir de commits/PRs (hoy es manual según
  `CHANGELOG.md`)

## 10. Documentación (P2, pero barata de hacer)

- [ ] ⏳ Sigue pendiente tras 6.1.0: screenshots actualizados del UI
  rediseñado. No se pudo completar en esta release -- no hay forma de
  guardar a disco las capturas del panel de navegador con las
  herramientas disponibles en la sesión que implementó el resto de esta
  lista.
- [ ] Documentar el formato de mensajes WebSocket (útil si en algún
  momento alguien más contribuye)
- [ ] Sección de arquitectura ampliada explicando el patrón
  módulo-por-feature en `backend/app/`

## 11. Integración entre features (P0/P1 -- conecta lo ya planeado, no features nuevas sueltas)

Estas no son features aisladas: son puntos donde dos o más ítems de arriba
deberían compartir lógica o UI en vez de construirse por separado. Vale la
pena resolverlas mientras se planea cada feature individual, no después.

- [x] ✅ Shipped en 6.2.0: Dashboard/Overview unificado como vista de
  entrada por defecto -- una card por disco con badge de boot, salud,
  barra de espacio, y badge de rendimiento vs. categoría esperada
  (reutilizando el historial de benchmark, sin endpoint nuevo).
- [ ] Correlación Health + Benchmark: cruzar historial de
  temperatura/salud (sección 3) con historial de benchmark (sección 2)
  para detectar degradación de rendimiento asociada a salud/temperatura,
  no mostrarlos como datos sueltos
- [ ] Reutilizar `windows_detector.py` (planeado para el treemap, sección
  5) también para marcar el disco de boot (sección 1) -- misma detección
  subyacente, no duplicar lógica
- [ ] Canal único de notificaciones: TRIM status y demás recomendaciones
  (sección 4) deben entrar al mismo sistema de tray notifications que ya
  existe para low disk space / predicted failure, no crear un mecanismo de
  alertas nuevo
- [x] ✅ Shipped en 6.1.0: Actividad en vivo + Benchmark -- la actividad de
  I/O en tiempo real (sección 2) advierte "disco con actividad alta, el
  benchmark puede dar resultados falseados" antes de correrlo.
- [ ] Snapshot de diagnóstico para soporte: botón "Generar reporte de
  diagnóstico" que junte specs + SMART + espacio + config en un archivo
  para adjuntar a un issue de GitHub. Distinto de "export/reporting" --
  ver resolución del conflicto de scope abajo.
- [x] ✅ Shipped en 6.1.0: Config centralizada -- `settings.py` es ahora el
  único lugar para todos los toggles/preferencias (autostart, último disco
  seleccionado, además de los que ya existían). Resuelto junto con la
  Settings UI, no como mecanismo separado.

---

## Conflicto de scope -- resuelto

~~Claude Code propuso "Export drive/health/partition data (CSV/JSON)" pero
`export/reporting` estaba listado explícitamente como fuera de scope en
`DiskInfo-project-plan.md`.~~

**Resuelto**: se separó "reporting" (PDF, automatizado, programado,
enviado a algún lado -- sigue fuera de scope) de "export simple" (CSV/JSON
de datos ya mostrados en pantalla -- ahora sí en scope). El mismo criterio
desbloquea el "Snapshot de diagnóstico para soporte" de la sección 11:
es una herramienta de troubleshooting, no reporting. Ver la sección
"Scope clarification: export vs. reporting" en `DiskInfo-project-plan.md`
para el detalle.

## Explícitamente fuera de scope (confirmado)

Redundante con `DiskInfo-project-plan.md`, pero para que quede todo en un
solo lugar: resize de particiones, clonado de disco, reporting (PDF /
automatizado / programado -- ver resolución arriba), discos de red, CLI,
encriptación, localización, soporte cross-platform.

---

## Próximos pasos

1. ~~Resolver el conflicto de scope de export/reporting~~ -- hecho (6.1.0).
2. ~~Implementar los 10 ítems + testing infra + config centralizada~~ --
   hecho, shipped en 6.1.0 (2026-08-14). Ver `CHANGELOG.md`.
3. ~~Continuar secciones 1/2 + salud + Dashboard + robustez~~ -- hecho,
   shipped en 6.2.0 (2026-08-14). Ver `CHANGELOG.md`.
4. ~~La sección 8 (robustez) se sigue resolviendo en paralelo~~ -- 6.2.0
   sumó logging, tests de integración WS, y linting/CI. Quedan: manejo de
   errores uniforme entre módulos, y UX explícita de reconexión WS por vista.
5. ~~Config centralizada (sección 11) junto con Settings UI~~ -- hecho (6.1.0).
6. Mantener este archivo actualizado -- hecho para 6.2.0; sigue aplicando
   hacia adelante.

**Pendiente real, arrastrado de 6.1.0 y 6.2.0**: screenshots del README --
sigue bloqueado por limitación de herramientas, no por decisión de alcance.

**Decisiones informadas, no pendientes**: generación PCIe y
controlador/chipset (sección 1) fueron investigadas en 6.2.0 contra
hardware real y descartadas por falta de una fuente de datos confiable --
no son "trabajo por hacer", son ítems cerrados con una razón documentada.

**Próximo paso sugerido**: el treemap de uso de disco (sección 5) sigue
siendo la pieza grande sin tocar del propósito original -- retomar en
cuanto se comparta `diskinfo-space-viz-plan.md`. Mientras tanto, de lo que
queda sin marcar en las secciones P0/P1, "detección de discos USB recién
conectados en vivo" (sección 3) y "atajo de teclado global" (sección 7)
son mejoras chicas y aisladas si se quiere una release más corta antes del
treemap.
