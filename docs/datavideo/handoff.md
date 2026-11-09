# Punto de partida: estado, siguientes pasos y cuentas

Este documento es la memoria del proyecto entre sesiones. Claude Code lo lee al empezar (lo exige `CLAUDE.md`) y lo actualiza al terminar cada sesión de trabajo: **Estado actual** y **Siguientes pasos** deben reflejar siempre la realidad del repositorio.

Arquitectura confirmada: [`architecture.md`](architecture.md).

---

## 1. Estado actual

Última actualización: **9 de noviembre de 2026**, rama `main`.

**Hecho y probado (`app/datavideo/`):**

| Módulo | Qué hace |
|---|---|
| `locale.py`, `facts.py`, `figures.py` | Formato es-ES/en-US (números, porcentajes, fechas, meses); datos con etiqueta, valor, detalle y fuente con licencia; verificación de cifras |
| `sources/ine.py` | Cliente de la API Tempus del INE: descarga, valida y conserva los valores como decimales exactos. Licencia CC BY 4.0 verificada |
| `stories/regional_ranking.py` | Ranking por comunidades del último mes publicado por todas (empates, Ceuta y Melilla como ciudades autónomas) y sus datos. Historia `ipc_anual_ccaa` (tabla 76140) |
| `script.py` | Guion JSON verificado: cifras por segmento, 4–7 segmentos de 30 palabras como máximo, escenas existentes, `big_number` con un dato; reintenta y bloquea |
| `channels.py` | Perfiles `channels/*.toml` con historias y `[publish]` (perfil de Upload-Post, redes, privacidad) |
| `scenes/` | `ranking`, `big_number` y `source_card` en 9:16 y 16:9, con el tercio inferior libre para subtítulos |
| `timeline.py`, `audio.py` | Una síntesis de toda la narración con Azure, segmentos alineados por palabra, subtítulos del motor original; voz normalizada a −14 LUFS |
| `render.py` | Pista de escenas con la duración de cada segmento y montaje con `video.generate_video` del motor original, sin música |
| `qa.py` | Bloquea por tamaño, audio, duración, desfase con la narración, volumen o subtítulos |
| `packaging.py` | Título, descripción con fuente, atribución, mes, aviso de IA y de no asesoramiento, etiquetas |
| `store.py`, `pipeline.py` | Carpeta por historia con un artefacto por paso; reanudable, no repite historias publicadas, no publica sin licencia verificada ni controles superados y nunca reintenta solo una subida sin confirmar |
| `publish.py`, `notify.py`, `digest.py` | Upload-Post con la clave de `.env`; Telegram solo para bloqueos, fallos y resumen semanal |
| `cli.py` | `produce`, `run` (produce y publica) y `report` (resumen semanal) |

- **Cómo se usa** (claves en `.env`):
  ```bash
  uv run --env-file .env --no-sync python -X utf8 -m app.datavideo.cli produce tu_dinero_es
  ```
  `run` en lugar de `produce` también publica; `report` envía el resumen semanal. Los vídeos quedan en `storage/datavideo/<canal>/<historia>/final.mp4`.
- **Primer Short real (9 de noviembre de 2026):** `storage/datavideo/tu_dinero_es/ipc_anual_ccaa_2026_09/final.mp4`, inflación anual por comunidades de septiembre de 2026: 38 s, 5 escenas, −15,2 LUFS, controles superados. Producirlo cuesta ~55 s.
- **Sin publicar todavía:** el clasificador de seguridad de Claude Code bloqueó el comando de subida. El propietario lo ejecuta a mano (`run` en vez de `produce`); sube en **privado** al canal personal de pruebas (perfil `default`).
- Voz del canal 1: `es-ES-TristanMultilingualNeural-V2-Male` (castellano). Muestras de otras cinco voces disponibles si se quiere cambiar.
- Pruebas: `uv run --no-sync python -X utf8 -m pytest -q test/services/test_datavideo_*.py` → 160 pruebas en ~5 s (necesitan FFmpeg).
- La batería completa del proyecto original (~3.200 pruebas, 12–14 min) tiene 9 fallos **heredados** en pruebas de audio con Python 3.13 (`test_remote_speech_complete_decode`, `test_webui_bgm`, `test_webui_custom_audio_upload`, `test_bgm_decoded_audio`). No se ha tocado código del proyecto original.

**Decisión del propietario (9 de noviembre de 2026):** REE queda descartada. El canal 1 se construye sobre INE y Eurostat, con el vídeo largo semanal como formato principal y los Shorts como entrada a él. Facebook queda fuera definitivamente.

**Nombres de los canales** (handles de YouTube y dominios .com libres el 9 de noviembre de 2026): `your_money_us` → *The Wallet Census* (`@WalletCensus`), `mundo_es` → *Medir el Mundo* (`@MedirElMundo`), `space_en` → *The Apogee Almanac* (`@ApogeeAlmanac`). `tu_dinero_es` conserva *Tu Dinero en Datos*, con `@TuDineroDatos`: `@TuDineroEnDatos` es de otra persona.

**Altas a 9 de noviembre de 2026:**
- **YouTube** (cuenta de Google `guillermomc007@gmail.com`): existen el canal personal `@guillermomartin2857` y *The Apogee Almanac*. Crear más canales exige funciones avanzadas: teléfono y, además, vídeo, documento de identidad o historial del canal (Studio → Configuración → Canal → Acceso a funciones). El canal personal hace de canal de pruebas. Documento de identidad enviado, en revisión (hasta 24 horas). Después, crear *Tu Dinero en Datos*, *The Wallet Census* y *Medir el Mundo*.
- **OpenAI y Upload-Post:** claves en `.env`, comprobadas contra cada API. Upload-Post está en plan Free con 2 perfiles: `default` (pruebas, conectado al canal personal de YouTube) y `tu_dinero_es` (canal 1, con Instagram conectado; falta el canal de YouTube cuando exista).
- **Azure:** recurso Speech `datavideo-voz` en `northeurope`, plan gratuito F0. `AZURE_SPEECH_KEY` en `.env`, comprobada con `voice.tts` del motor original: `es-ES-AlvaroNeural-V2-Male` genera audio con marcas de tiempo por palabra; `es-ES-AlvaroNeural-Male-V2`, el nombre del perfil actual, falla.
- **Instagram:** `bear.5796587` es de pruebas de otro software y no debe usarse (sesión cerrada en Chrome). Cuenta del canal 1 `@tudinerodatos`, creada con `guillermomc007@gmail.com` y ya profesional (Creador, categoría *Media/news company*). Nombre público *Tu Dinero en Datos*. Conectada al perfil `tu_dinero_es` de Upload-Post (comprobado por la API). Falta foto de perfil y biografía. Para los demás canales, alias de Gmail (`guillermomc007+canal@gmail.com`).
- **Telegram:** bot `@avisos_datavideo_bot`, con token comprobado y `TELEGRAM_CHAT_ID` en `.env`.
- `config.toml` ya tiene los ajustes no secretos de H1 (`youtube`, `private`, `northeurope`, `default`).

---

## 2. Puesta en marcha en local (VS Code + Claude Code)

1. Instala Git, [uv](https://docs.astral.sh/uv/), FFmpeg y VS Code con la extensión de Claude Code.
2. Clona y entra:
   ```bash
   git clone https://github.com/gmartincor/MoneyPrinterTurbo.git
   ```
   ```bash
   cd MoneyPrinterTurbo
   ```
3. Instala dependencias:
   ```bash
   uv sync --frozen
   ```
4. Comprueba que todo funciona:
   ```bash
   uv run --no-sync python -X utf8 -m pytest -q test/services/test_datavideo_*.py
   ```
5. Crea un archivo `.env` en la raíz (ya está en `.gitignore`, **nunca se sube**) con las claves de la sección 3, una por línea, por ejemplo `OPENAI_API_KEY=...`. La clave de Azure Speech va también en `.env` (`AZURE_SPEECH_KEY`). Su región va en `config.toml` (también ignorado por Git; se crea solo al arrancar la app por primera vez a partir de `config.example.toml`), en la sección `[azure]`: `speech_region`. Para ejecutar con las claves del `.env`:
   ```bash
   uv run --env-file .env --no-sync python -X utf8 -m pytest -q test/services/test_datavideo_*.py
   ```
6. Abre la carpeta en VS Code. Claude Code carga `CLAUDE.md`, que le indica leer las skills, este documento y la arquitectura antes de trabajar. Pídele: *"Sigue con los siguientes pasos de docs/datavideo/handoff.md"*.
7. Para traer mejoras del proyecto original (una vez):
   ```bash
   git remote add upstream https://github.com/harry0703/MoneyPrinterTurbo.git
   ```
8. Activa **GitHub Actions** en tu fork (pestaña *Actions* del repositorio → activar flujos). Al subir cambios a `main`:
   - Si solo tocan nuestro código (`app/datavideo/`, `channels/`, sus pruebas), documentación, `.claude/` o `CLAUDE.md`, se ejecutan **solo nuestras pruebas** (`datavideo.yml`, ~1–2 min contando la instalación).
   - Las ~3.200 pruebas del proyecto original (`ci.yml`, ~14 min) solo se ejecutan si se toca código del proyecto original, o a mano desde la pestaña *Actions* (botón *Run workflow*). Conviene lanzarlas a mano después de traer cambios del proyecto original.
   - Ninguna de las dos bloquea tu trabajo: se ejecutan en GitHub en segundo plano.

**Nunca pegues claves en el chat.** Van solo en `.env` o en las variables del servidor.

---

## 3. Cuentas y claves, en orden

| # | Servicio | Para qué | Qué hacer | Coste | Variable | Cuándo |
|---|---|---|---|---|---|---|
| 1 | **OpenAI Platform** | Guionista y juez (GPT-6.1 Sol) | Crear clave de API y **poner un límite de gasto mensual** (p. ej. 20 $) | ~3–10 $/mes | `OPENAI_API_KEY` | H1 |
| 2 | **Azure (Speech)** | Voz | En el portal de Azure, crear un recurso *Speech* en *North Europe* (West Europe no admite clientes nuevos): plan gratuito **F0** para H1 y **pago por uso (S0)** al empezar a publicar. Copiar la clave a `.env` (`AZURE_SPEECH_KEY`; `timeline.py` la pasa a `config.azure` en memoria) y la región a `config.toml` → `[azure] speech_region` | ~1–5 $/mes | `AZURE_SPEECH_KEY` | H1 |
| 2b | **ElevenLabs** (opcional, más adelante) | Voz más natural | Solo si las estadísticas de un canal muestran que la voz hace que la gente se vaya. Cuenta separada de la de tus agentes, voz creada con Voice Design, y en el perfil `voice.name = "elevenlabs:<voice_id>"` | 22–99 $/mes | `ELEVENLABS_API_KEY` | Si los datos lo justifican |
| 3 | **Google / YouTube** | Canales | Verificación en dos pasos. Crear un **canal de pruebas** (privado, sin verificar por teléfono) y la cuenta de marca *Tu Dinero en Datos*. Cada número de teléfono solo verifica **2 canales al año** y la verificación es necesaria para miniaturas propias y vídeos de más de 15 min: los 4 canales necesitan 2 números | 0 € | — | H1 (pruebas), H2 |
| 4 | **Google Cloud** | Estadísticas y API de YouTube | Proyecto nuevo; activar *YouTube Data API v3* y *YouTube Analytics API*; pantalla de consentimiento OAuth en **Producción** (nunca *Testing*; sin verificar sirve para uso propio con menos de 100 usuarios); cliente OAuth de escritorio. Desde el 2 de noviembre de 2026 los vídeos subidos desde proyectos sin auditar ya no quedan privados: la **auditoría** no se solicita (decisión del propietario), solo sería obligatoria para superar 100 `videos.insert` al día | 0 € | `GOOGLE_OAUTH_CLIENT_FILE` (ruta al JSON) | H3 |
| 5 | **Instagram** | Reels y carruseles | Cuenta profesional por canal, creada al lanzar cada uno | 0 € | — | H2 |
| 6 | **Upload-Post** | Publicar | Plan **Free** para H1 (2 perfiles, 10 subidas/mes). Desde H2, plan **Basic** (5 perfiles: los 4 canales y el de pruebas), un perfil por canal con YouTube e Instagram conectados. En H1 fijar `upload_post_platforms = ["youtube"]` y `upload_post_youtube_privacy_status = "private"`: los valores por defecto son TikTok + Instagram y `public` | 0 $ en H1; luego 24 $/mes, o 16 $/mes con pago anual (192 $) | `.env`: `UPLOAD_POST_API_KEY` (`publish.py` la pasa con `cross_post_video(account=...)`). Perfil, redes y privacidad en `[publish]` del perfil del canal | H1 (Free), H2 (Basic) |
| 7 | **Telegram** | Avisos y veto | Crear bot con @BotFather y obtener tu `chat_id` | 0 € | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | H2 |
| 8 | **Datos España** | Canal 1 | INE y Eurostat responden sin registro (comprobado) | 0 € | — | H1 |
| 9 | **Datos EE. UU.** | Canal 2 | Registro gratuito en BLS, EIA y FRED | 0 € | `BLS_API_KEY`, `EIA_API_KEY`, `FRED_API_KEY` | H4 |
| 10 | **Datos mundo** | Canal 3 | Banco Mundial, Eurostat, Our World in Data: sin registro | 0 € | — | H5 |
| 11 | **NASA** | Canal 4 | Clave gratuita en api.nasa.gov | 0 € | `NASA_API_KEY` | H5 |
| 12 | **Servidor** | Funcionar 24/7 | VPS de 4 núcleos y 8 GB (o tu PC encendido) | ~10 €/mes | — | H2 |
| 12b | **Música con licencia comercial** | Fondo musical | Elegir una biblioteca que permita uso comercial en YouTube e Instagram, o publicar sin música | Según biblioteca | — | H2 |
| 13 | **Amazon Afiliados** (ES y US) | Ingresos por afiliación | Alta en ambos programas | 0 € | — | H3 |
| 14 | **AdSense + W-8BEN** | Cobrar de YouTube | Vincular al pedir el Programa de Partners; rellenar el formulario fiscal de EE. UU. | 0 € | — | Al acercarse a 1.000 suscriptores |
| 15 | **Gestor fiscal** | Hacienda | Consultar **antes del primer ingreso**: alta censal, autónomo (tarifa plana en torno a 80 €/mes el primer año) e IRPF | — | — | Antes de cobrar |
| 16 | **Dominio + Cloudflare Pages** | Web de datos | Registrar dominio y crear el proyecto | ~1 €/mes | `CLOUDFLARE_API_TOKEN` | H5 |

Hoy se leen `OPENAI_API_KEY`, `AZURE_SPEECH_KEY`, `UPLOAD_POST_API_KEY`, `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`. `BLS_API_KEY`, `EIA_API_KEY`, `FRED_API_KEY`, `NASA_API_KEY`, `GOOGLE_OAUTH_CLIENT_FILE` y `CLOUDFLARE_API_TOKEN` son nombres previstos para código que aún no existe.

---

## 4. Licencias pendientes de verificar

Una fuente solo puede usarse en un vídeo publicado cuando su `Source.license_verified` es `True`. Revisar y anotar la licencia exacta en el código de cada fuente:

- Ministerio (carburantes), Banco de España (ojo: el Euríbor diario tiene restricciones de EMMI; usar el dato mensual oficial).
- Banco Mundial (CC BY 4.0 según su catálogo), Our World in Data.
- NASA (sin derechos de autor en general, sin usar su logo; hay excepciones de terceros), ESA/Webb (CC BY 4.0).
- FRED (las series con la palabra "Copyright" en sus notas exigen permiso del titular; FRED exige además mostrar "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis").
- Mapas: Natural Earth (dominio público), IGN/CNIG (CC BY 4.0).
- Fuente tipográfica BeVietnamPro (OFL) y biblioteca de música elegida.

**Comprobadas el 9 de noviembre de 2026:**

- **INE** (anotada en `sources/ine.py`): CC BY 4.0, uso comercial permitido sin autorización. Citar "Elaboración propia con datos extraídos del sitio web del INE: www.ine.es" y la fecha de última actualización; no sugerir que el INE participa o respalda el vídeo. Solo cubre información cuya fuente original sea el INE.
- **Eurostat** (falta anotarla al crear su cliente): uso comercial permitido citando la fuente, sin licencia escrita. Antes hay que retirar los datos de países fuera de la UE, la AELC y los candidatos, y los de fuentes ajenas a Eurostat.
- **BLS y EIA:** dominio público; citar la fuente (EIA, con fecha). Sin sus logos ni fotografías de terceros.

---

## 5. Siguientes pasos

### H1 — Primer Short real, en privado (casi terminado)

| # | Tarea | Estado |
|---|---|---|
| 1 | Subir el primer Short en privado al canal de pruebas y revisarlo | **Lo hace el propietario:** `uv run --env-file .env --no-sync python -X utf8 -m app.datavideo.cli run tu_dinero_es` |
| 2 | Banco de pruebas de guiones: 20 casos, GPT-6.1 Sol frente a Terra; anotar el resultado en `architecture.md` | Pendiente |
| 3 | Confirmar la voz escuchando las muestras (Tristán elegida por defecto) | Propietario |

### H2 — Canal 1 publicando solo

| # | Tarea | Aceptación |
|---|---|---|
| 1 | Planificador | `run` cada noche y `report` cada lunes en el servidor (o el Mac encendido), con registro de salida. Requiere decidir dónde corre |
| 2 | Pasar el canal 1 a producción | Cuando YouTube apruebe el DNI: crear *Tu Dinero en Datos* (`@TuDineroDatos`), conectarlo al perfil `tu_dinero_es` de Upload-Post, contratar el plan Basic y cambiar `[publish]` a `user = "tu_dinero_es"`, `platforms = ["youtube", "instagram"]`, `privacy = "public"` |
| 3 | Más historias | Otras tablas del INE (vivienda por comunidades, paro de la EPA, salarios) y comparaciones con Europa (Eurostat). Exige historias trimestrales y anuales, no solo mensuales, y un juez que elija entre varias candidatas |
| 4 | Vídeo largo semanal 16:9 | Formato principal: 8–12 min con capítulos y miniatura, a partir de varias historias de la semana |
| 5 | Límites de gasto | Coste por guion y por voz con tope mensual por canal; pasar Azure a S0 cuando se supere el plan gratuito |
| 6 | Instagram | Foto de perfil y biografía; carruseles con `/api/upload_photos` |
| 7 | Música | Elegir biblioteca con licencia comercial o seguir sin música |

### H3 — Estadísticas y más fuentes
Más fuentes oficiales con licencia verificada, estadísticas, afiliados.

### H4 — Aprendizaje y canal 2
Bucle de estadísticas → pesos del juez; canal `your_money_us`.

### H5 — Canales 3 y 4 y web
`mundo_es`, `space_en` y la web de datos.

---

## 6. Previsión económica

Estimación propia, con mucha incertidumbre. Los ingresos dependen de que los canales enganchen, y eso no se puede saber antes de publicar.

**Costes:** ~30 €/mes con 1 canal; ~40–50 €/mes con 4 canales (voz con Azure Speech). Primer año: ~450–550 €. ElevenLabs añadiría 22–99 $/mes si algún canal lo justifica.

**Requisito para cobrar anuncios:** 1.000 suscriptores y 4.000 horas de visualización en 12 meses por canal (equivale a unas 60.000 visitas de vídeos largos con ~4 minutos vistos de media), o 10 millones de visualizaciones de Shorts en 90 días. La página oficial no anuncia una subida del umbral; sí que hay condiciones nuevas del Programa de Partners desde el 1 de febrero de 2027, que deben aceptarse en YouTube Studio antes del 31 de enero de 2027.

**Riesgo principal para los ingresos:** la política de contenido no auténtico de YouTube (aclarada el 16 de julio de 2026) excluye de la monetización el contenido genérico, repetitivo o de plantilla y los personajes de IA que se presentan como expertos humanos en finanzas. Cada vídeo debe tener un enfoque propio, sin presentador ficticio y sin consejos.

| Escenario | Qué pasa | Ingresos/mes al mes 12 | Margen/mes al mes 12 |
|---|---|---|---|
| Pesimista (el más probable) | Ningún canal o uno llega a monetizar | 0–50 € | 0 a −50 € → se pausan canales y se reduce el gasto |
| Base | 1–2 canales monetizados, 20.000–60.000 visitas largas/mes en total | 150–450 € | +100 a +400 € |
| Optimista | 3–4 canales monetizados y uno despega | 1.500–4.000 € | +1.450 a +3.950 € (a partir del mes 15–24) |

A esto hay que restar impuestos y, si corresponde, la cuota de autónomo (consultar al gestor).
