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

## 1. Identificación y clasificación de discos (P0 -- núcleo)

- [x] ✅ Shipped en 6.1.0: reemplazada la detección por string del nombre
  del modelo por `MSFT_PhysicalDisk` (WMI `root\Microsoft\Windows\Storage`),
  que expone `MediaType`, `SpindleSpeed` y `BusType` reales -- misma fuente
  que usa Windows Settings y `Get-PhysicalDisk`.
- [ ] Detectar bus real: SATA vs NVMe vs PCIe, y generación (Gen3/Gen4/Gen5)
  -- `BusType` de `MSFT_PhysicalDisk` es el punto de partida, ver ítem de
  arriba (se obtiene como side-effect del ítem confirmado, pero la
  generación específica queda para más adelante)
- [ ] Mostrar controlador/chipset al que está conectado cada disco (detecta
  lanes compartidos)
- [ ] Marcar claramente cuál es el disco de arranque (boot)
- [ ] Mapear disco físico → letras de unidad/particiones que contiene

## 2. Rendimiento y velocidad (P0 -- núcleo)

- [x] ✅ Shipped en 6.1.0: el benchmark ya no mide contra el page cache de
  Windows -- usa `FILE_FLAG_NO_BUFFERING` con I/O alineado a sector vía
  `win32file`/`mmap` para bypassear el cache y medir el disco de verdad.
- [x] ✅ Shipped en 6.1.0: parámetros `total_mb` expuestos en la UI como
  presets (Quick/Standard/Thorough).
- [ ] Benchmark de lectura/escritura ya existe -- agregar test de latencia /
  IOPS (no solo throughput secuencial)
- [x] ✅ Shipped en 6.1.0: historial de benchmarks (disco, fecha, promedio
  lectura/escritura) guardado local (SQLite), con tabla de tendencia bajo
  el gráfico.
- [ ] Benchmark programado (ej. semanal, opcional)
- [ ] Detección de discos "lentos" vs su categoría esperada (ej. NVMe
  rindiendo como SATA → alerta de mal montaje/modo AHCI)
- [x] ✅ Shipped en 6.1.0: actividad de I/O real en vivo por disco vía
  `psutil.disk_io_counters(perdisk=True)`, transmitida por el WebSocket
  existente, mostrada como sparkline en la card de cada disco.

## 3. Salud y estado (P0/P1)

- [ ] Historial de temperatura/salud en el tiempo (gráfico, ya se usa Chart.js)
- [ ] Umbrales configurables de alerta (temp, % vida restante)
- [ ] Lectura de atributos SMART crudos (raw values) para usuarios avanzados
- [ ] TBW (Total Bytes Written) / ciclos de escritura estimados cuando SMART lo exponga (P1)
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
- [x] ✅ Shipped en 6.1.0: toggle de autostart editable desde la app --
  verificado escribiendo y leyendo la clave de registro directamente
  (`HKCU\...\Run`), la misma que usa el instalador.
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
- [ ] Tests de integración para los endpoints WebSocket (simular
  reconexión, mensajes fuera de orden)
- [ ] Manejo consistente de errores: WMI no disponible, disco desconectado
  a mitad de operación, permisos insuficientes -- definir un formato de
  error uniforme entre todos los módulos, no ad-hoc por feature
- [ ] Logging a archivo (rotación básica) para debugging cuando alguien
  reporta un issue -- hoy el Troubleshooting del README pide "abrir un
  issue" sin mencionar logs adjuntos
- [ ] Manejo de reconexión de WebSocket en el frontend si el backend se
  reinicia o hay hiccup (parcialmente cubierto: `ws-client.js` ya
  reconecta con backoff, falta UX explícita en cada vista)
- [ ] Linting/formatting configurado (black/ruff para Python, eslint si
  corresponde) y agregado al workflow de CI existente
  (`.github/workflows/`)
- [ ] Revisar necesidad real de "ejecutar como administrador" por feature
  -- hoy es un caso documentado en Troubleshooting, pero sería mejor
  detectar en runtime qué falló por permisos y pedir elevación solo cuando
  haga falta, en vez de requerir admin siempre

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

- [ ] Dashboard/Overview unificado: vista inicial con resumen de todos los
  discos (score simple: salud + espacio libre + rendimiento vs. categoría
  esperada), en vez de que el usuario tenga que entrar pestaña por pestaña
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

1. ~~Resolver el conflicto de scope de export/reporting~~ -- hecho.
2. ~~Implementar los 10 ítems + testing infra + config centralizada~~ --
   hecho, shipped en 6.1.0 (2026-08-14). Ver `CHANGELOG.md`.
3. ~~De la sección 1 y 2, lo que quede fuera de esta release, queda para la
   siguiente~~ -- aplicado: bus/generación PCIe detallada, controlador/
   chipset, disco de boot, mapeo físico→letras, IOPS/latencia, benchmark
   programado, y detección de discos "lentos vs. categoría esperada" siguen
   sin marcar, quedan abiertos en las secciones 1 y 2.
4. La sección 8 (robustez) se sigue resolviendo en paralelo con cada
   feature nueva -- esta release sumó pytest; falta logging a archivo,
   manejo de errores uniforme, tests de integración WS, y linting/CI.
5. ~~Config centralizada (sección 11) junto con Settings UI~~ -- hecho.
6. Mantener este archivo actualizado -- hecho para esta release; sigue
   aplicando hacia adelante.

**Pendiente real de 6.1.0**: el ítem #11 (screenshots del README) no se
pudo completar por limitación de herramientas, no por decisión de alcance
-- sigue en el backlog tal cual.

**Próximo paso sugerido**: de las secciones P0 (1 y 2) que quedaron sin
marcar, `IOPS/latencia además de throughput secuencial` y `detección de
discos lentos vs. categoría esperada` son las que más se acercan al
propósito original del proyecto y a lo que ya se construyó en 6.1.0 (el
benchmark y la detección de tipo de disco). Buenos candidatos para la
próxima ronda de planificación.
