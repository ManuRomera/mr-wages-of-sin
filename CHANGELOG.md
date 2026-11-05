# Cambios

## 1.1.1 (2026-11-05)

Revisión completa: el módulo se instala solo, está ordenado y todo sale del libro.

- **Autoinstalable de verdad.** La importación automática de 1.0.0 fallaba al activarse. Ahora, en un mundo nuevo, se importa todo en una carpeta **Wages of Sin** de cada pestaña (escenas por zonas, actores por grupos, diarios, objetos, tablas y macros) y las macros quedan en la barra. Botón de reimportación en Configuración; los personajes de los jugadores no se pisan.
- **Retratos arreglados.** Los 100 retratos de las órdenes salían casi negros (se perdía la máscara de tinta); ahora son los del libro, con su token. Los cazarrecompensas, la fauna y los presos usan su arte real en lugar de capturas de página.
- **Arte sin maquetación.** Escenas, mapas y planos recortados sin texto del libro; miniaturas de escena; iconos nuevos.
- **Todo el texto del libro.** Órdenes, manual, cazarrecompensas, estaciones y tablas se leen del texto de la tradumaquetación (antes eran líneas sueltas del PDF con palabras partidas). Las tablas de dados salen en filas.
- **Datos reales.** Se retiran las cifras, tablas y reglas que no eran del libro (pagos por BL, generador, sentencias, simulador del Infierno Verde, estadísticas de presos y fauna inventados). Fichas de naves, cazarrecompensas, personal, presos (100 en el registro, 27 con ficha y retrato), fauna (10 criaturas) y las 13 armas de prisión, con las cifras del libro.
- **Terminal rehecha** con lo que el libro define: órdenes, tabla de niveles y pago, oráculo y sobornos.
- Retratos del personal de dirección y dos presos, e iconos, generados para el módulo (indicado en cada ficha).

## 1.0.0 (2026-11-05)

Primera publicación completa en español de **Wages of Sin (MRPG-M6)** para *Mothership 1e* en Foundry VTT v13/v14.

- **Las 100 Órdenes de Busca completas (`ordenes` y `objetivos`)**:
  - Las 100 órdenes (`#01` a `#100`) maquetadas en 5 diarios multipágina en español con su código de personaje de 6 dígitos, Nivel de Busca (`BL 1–10`), estado (`Vivo` / `Muerto`), anuncio, informe público para los jugadores y sección privada para el Guardián (`<section class="secret">`).
  - Los **100 objetivos como actores (`creature`)** en el compendio `objetivos`, cada uno con su retrato extraído del libro, token circular y estadísticas de combate e instinto listas para tirar.
- **Terminal interactiva de Recompensas y ODC (`TerminalRecompensas`)**:
  - Buscador y filtro instantáneo de las 100 órdenes por nombre, ubicación (Absalom Station, Anvollapolis, Balonov, HypeLabs Domia, Utpala, Offit ODC…), delito o Nivel de Busca (`BL 1–10`).
  - Botón **«Mostrar Cartel (Sin spoilers)»** que publica en el chat el cartel de «SE BUSCA» únicamente con la información pública para los jugadores, con botón de **Oráculo BL (`1d10 ≤ BL`)**.
  - **Generador procedural de contratos** (objetivo, delito, complicación y pago según BL) y **asistente de rastreo** (listas de pasajeros, terminales de venta, pruebas forenses, antecedentes y cómplices).
  - **Calculadora de Delitos de Jugadores y Juicio**: evalúa las pruebas dejadas (`1d10 ≤ nivelPrueba`), actualiza el `BL` de la tripulación y dicta sentencia (multa, trabajos forzados o traslado en el *MPT «Bus»* a la Luna Carcelaria ODC en Baclite).
- **Los 10 Cazarrecompensas Rivales con nombre propio**:
  - *01 La Langosta*, *02 Assassin Kult*, *03 Veteranos (Andra Arlotti)*, *04 Ivo Salomon (Parásito)*, *05 Red Taskr*, *06 Emira Churchill (Desmontada)*, *07 El Soñador: Alf Moss*, *08 Edgars Crismondi*, *09 Amaruq Borges (Memorius)* y *10 Cazador 854 alias «Sr. Bichos»*, con retrato, token, **figura de cuerpo entero** y sus tablas de tácticas `1d5`.
- **Módulo de campaña «La ODC: Baclite (La Luna Carcelaria)» y «El Infierno Verde» (`aventura-baclite`)**:
  - **16 escenas** listas para jugar: portada, Mapa de Salto del Sector a doble página, estaciones principales, planos de la prisión ODC en versión para la mesa (sin secretos) y versión para el Guardián (con dotación de atalayas y cámaras), plano de celda para esconder contrabando, mapa del Infierno Verde (versión mesa y versión Guardián) y planos de cubierta de las naves.
  - Personal de la ODC (`S YY/XX`) con tirada automatizada de **Soborno (`1d100 < Soborno`)**, líderes y presos (`#YYXX`) de las bandas (*23 Arms*, *Sindicato Stratemeyer*, *Sindicato de Presos*), **Fauna de Offit** (*Larvas*, *Chupaárboles*, *Pseudohienas*, *Basilisco*, *Acechador del dosel*) y simulador de supervivencia y forrajeo en el Infierno Verde.
  - Paquete completo para **MR- Dirección** (`content/direccion-es.json`) con lecturas en voz alta y relojes de campaña.
- **Las 3 Naves nuevas (`naves`) y Armas/Equipos (`equipo`)**:
  - *MPT «Bus»* (*Valecore MPT-SC J2C-II*), *Hunter-Seeker* (*Gauss CR-Medusa J1C-II*) y *Veil of Night* (*Utpala Shipyards Magnum Opus J3C-VI*) con sus planos de cubierta a doble página y compatibilidad directa con **MR- Kit del Desguazador**.
  - Armas improvisadas de prisión (pincho, anillos, pilas en calcetín, látigo de cuchillas, hachuela, motosierra, bisturí), equipo de cazarrecompensas (pistola sedante, porra eléctrica, grilletes, TaskMaster, féretro de estasis) y kits de campaña.
  - Modo oscuro y accesibilidad compartidos con **MR- Mothership en español**.
