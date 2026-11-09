# Punto de partida: estado, siguientes pasos y cuentas

Este documento es la memoria del proyecto entre sesiones. Claude Code lo lee al empezar (lo exige `CLAUDE.md`) y lo actualiza al terminar cada sesión de trabajo: **Estado actual** y **Siguientes pasos** deben reflejar siempre la realidad del repositorio.

Arquitectura confirmada: [`architecture.md`](architecture.md).

---

## 1. Estado actual

Última actualización: **9 de noviembre de 2026**, rama `main`.

**Hecho y probado (`app/datavideo/`):**

| Módulo | Qué hace |
|---|---|
| `locale.py` | Formatea números, porcentajes y fechas en es-ES y en-US |
| `facts.py` | Modelo de dato (`Fact`) y de fuente (`Source`, con licencia y si está verificada) |
| `figures.py` | Comprueba que cada cifra de un texto aparece en los datos y rechaza números escritos con letra (es-ES, en-US) |
| `script.py` | Pide el guion en JSON (título + segmentos con datos y escena), lo verifica segmento a segmento, reintenta y bloquea si no pasa |
| `channels.py` | Carga y valida `channels/*.toml`; crea el generador de texto por rol (guionista, juez) |
| `theme.py`, `scenes/` | Interfaz de escenas, render a clip y escena `hourly_prices` en 9:16 y 16:9 |
| `electricity.py` | Resume los 24 precios PVPC del día en datos (hora más barata y más cara, media, franja de 3 h, diferencia) |

- Perfil creado: `channels/tu_dinero_es.toml` con la voz provisional de Azure `es-ES-AlvaroNeural-Male-V2` (se elegirá la definitiva escuchando muestras; ese nombre está mal formado, ver tarea 8 de H1). Es el único perfil creado: faltan `your_money_us`, `mundo_es` y `space_en`.
- Pruebas: `uv run --no-sync python -X utf8 -m pytest -q test/services/test_datavideo_*.py` → todas pasan en ~2 segundos.
- La batería completa del proyecto original (~3.200 pruebas, 12–14 min) tiene 9 fallos **heredados** en pruebas de audio con Python 3.13 (`test_remote_speech_complete_decode`, `test_webui_bgm`, `test_webui_custom_audio_upload`, `test_bgm_decoded_audio`). Ya fallaban antes de este trabajo. Solo se ejecuta en local si se toca código del proyecto original; si no, la ejecuta GitHub Actions al subir a `main` (ver `CLAUDE.md`, *Verification Policy*).
- Decisión revisada: la voz, los subtítulos, la música y el montaje **los hace el motor del proyecto original**; nosotros solo aportamos datos, guion verificado y escenas. ElevenLabs deja de ser necesario de entrada.

**Automatización:** todavía no existe. Ningún punto de entrada (`cli.py`, API, WebUI) usa `app/datavideo/`, no hay planificador y el motor original (voz, subtítulos, montaje, publicación) aún no está conectado. No se puede generar un vídeo de principio a fin.

**Pendiente de bloqueo externo:**
- Faltan las cuentas y claves de la sección 3.

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
| 2 | **Azure (Speech)** | Voz | En el portal de Azure, crear un recurso *Speech* en *North Europe* (West Europe no admite clientes nuevos): plan gratuito **F0** para H1 y **pago por uso (S0)** al empezar a publicar. Copiar la clave a `.env` (`AZURE_SPEECH_KEY`, que `timeline.py` pasará a `config.azure`, porque el motor solo lee de ahí) y la región a `config.toml` → `[azure] speech_region`. Mientras tanto, en desarrollo se puede usar Edge TTS (gratis) con `es-ES-AlvaroNeural-Male` | ~1–5 $/mes | `AZURE_SPEECH_KEY` | H1 |
| 2b | **ElevenLabs** (opcional, más adelante) | Voz más natural | Solo si las estadísticas de un canal muestran que la voz hace que la gente se vaya. Cuenta separada de la de tus agentes, voz creada con Voice Design, y en el perfil `voice.name = "elevenlabs:<voice_id>"` | 22–99 $/mes | `ELEVENLABS_API_KEY` | Si los datos lo justifican |
| 3 | **Google / YouTube** | Canales | Verificación en dos pasos. Crear un **canal de pruebas** (privado, sin verificar por teléfono) y la cuenta de marca *Tu Dinero en Datos*. Cada número de teléfono solo verifica **2 canales al año** y la verificación es necesaria para miniaturas propias y vídeos de más de 15 min: los 4 canales necesitan 2 números | 0 € | — | H1 (pruebas), H2 |
| 4 | **Google Cloud** | Estadísticas y API de YouTube | Proyecto nuevo; activar *YouTube Data API v3* y *YouTube Analytics API*; pantalla de consentimiento OAuth en **Producción** (nunca *Testing*; sin verificar sirve para uso propio con menos de 100 usuarios); cliente OAuth de escritorio. Desde el 2 de noviembre de 2026 los vídeos subidos desde proyectos sin auditar ya no quedan privados: la **auditoría** no se solicita (decisión del propietario), solo sería obligatoria para superar 100 `videos.insert` al día | 0 € | `GOOGLE_OAUTH_CLIENT_FILE` (ruta al JSON) | H3 |
| 5 | **Instagram** | Reels y carruseles | Cuenta profesional por canal, creada al lanzar cada uno | 0 € | — | H2 |
| 6 | **Upload-Post** | Publicar | Plan **Free** para H1 (2 perfiles, 10 subidas/mes). Desde H2, plan **Basic** (5 perfiles: los 4 canales y el de pruebas), un perfil por canal con YouTube e Instagram conectados. En H1 fijar `upload_post_platforms = ["youtube"]` y `upload_post_youtube_privacy_status = "private"`: los valores por defecto son TikTok + Instagram y `public` | 0 $ en H1; luego 24 $/mes, o 16 $/mes con pago anual (192 $) | `.env`: `UPLOAD_POST_API_KEY` (la pasará `publish/` con `cross_post_video(account=...)`, porque `upload_post.py` solo lee `config.toml`). `config.toml`: `upload_post_enabled`, `upload_post_username` | H1 (Free), H2 (Basic) |
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

`UPLOAD_POST_API_KEY`, `AZURE_SPEECH_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `BLS_API_KEY`, `EIA_API_KEY`, `FRED_API_KEY`, `NASA_API_KEY`, `GOOGLE_OAUTH_CLIENT_FILE` y `CLOUDFLARE_API_TOKEN` son nombres previstos: el código que los leerá aún no existe. Hoy solo se leen `OPENAI_API_KEY`, `ELEVENLABS_API_KEY` y las claves de `config.toml`.

---

## 4. Licencias pendientes de verificar

Una fuente solo puede usarse en un vídeo publicado cuando su `Source.license_verified` es `True`. Revisar y anotar la licencia exacta en el código de cada fuente:

- Ministerio (carburantes), Banco de España (ojo: el Euríbor diario tiene restricciones de EMMI; usar el dato mensual oficial).
- Banco Mundial (CC BY 4.0 según su catálogo), Our World in Data.
- NASA (sin derechos de autor en general, sin usar su logo; hay excepciones de terceros), ESA/Webb (CC BY 4.0).
- FRED (las series con la palabra "Copyright" en sus notas exigen permiso del titular; FRED exige además mostrar "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis").
- Mapas: Natural Earth (dominio público), IGN/CNIG (CC BY 4.0).
- Fuente tipográfica BeVietnamPro (OFL) y biblioteca de música elegida.

**Comprobadas el 9 de noviembre de 2026** (falta anotarlas en el código de cada fuente):

- **INE:** CC BY 4.0, uso comercial permitido sin autorización. Citar "Elaboración propia con datos extraídos del sitio web del INE: www.ine.es" y la fecha de última actualización; no sugerir que el INE participa o respalda el vídeo. Solo cubre información cuya fuente original sea el INE.
- **Eurostat:** uso comercial permitido citando la fuente, sin licencia escrita. Antes hay que retirar los datos de países fuera de la UE, la AELC y los candidatos, y los de fuentes ajenas a Eurostat.
- **BLS y EIA:** dominio público; citar la fuente (EIA, con fecha). Sin sus logos ni fotografías de terceros.

---

## 5. Siguientes pasos

### H1 — Primer Short real, en privado

| # | Tarea | Aceptación | Verificación |
|---|---|---|---|
| 1 | `sources/ine.py`: cliente de la API Tempus del INE | Cliente con timeout y validación; respuesta real guardada como fixture; produce `Fact` con la licencia CC BY 4.0 verificada. Se retiran `electricity.py`, `scenes/hourly_prices.py` y sus pruebas | Prueba de contrato con la fixture |
| 2 | `speech.py`: texto hablado es-ES/en-US | "0,082 €/kWh", "14:00", "181 %" y fechas se convierten a palabras que la voz lee bien | Pruebas unitarias |
| 3 | `timeline.py` con `voice.tts` del proyecto original | Pasa `AZURE_SPEECH_KEY` a `config.azure`, genera el audio con la voz del perfil y convierte los tiempos por palabra (`SubMaker`) en inicio y fin de cada segmento; subtítulos por frase con el texto mostrado | Pruebas unitarias con tiempos de ejemplo + prueba real con Edge TTS |
| 4 | Escenas `ranking`, `big_number` y `source_card` | Se ven bien en 9:16 y 16:9 | Imágenes de referencia + revisión visual |
| 5 | `render.py` | Renderiza las escenas en orden con la duración de cada segmento y llama a `task.generate_final_videos` del proyecto original (subtítulos, música, FFmpeg) para obtener el Short 9:16. `bgm_type` vacío hasta tener música con licencia: el valor por defecto del motor (`random`) usa `resource/songs` | Prueba de render corta |
| 6 | `store.py`, `pipeline.py`, `cli.py dry-run` | Ejecución completa para `tu_dinero_es` sin publicar, reanudable. La publicación se bloquea si alguna fuente tiene `license_verified` en falso (hoy nada lo comprueba) | Simulación de principio a fin |
| 7 | Banco de pruebas de guiones | 20 casos; comparar GPT-6.1 Sol y Terra; anotar resultado en `architecture.md` | Informe del banco |
| 8 | Elegir la voz | Generar muestras con 3–4 voces de Azure en español; el propietario elige una y se fija en el perfil. Formato correcto: `es-ES-AlvaroNeural-V2-Male` (`…-Male-V2` se resuelve a una voz inexistente; corregir perfil, prueba y `architecture.md`) | Revisión del propietario |

**Fin de H1:** un Short generado con datos reales de hoy, verificado, con voz, revisado por el propietario y subido en **privado** al canal de pruebas.

### H2 — Canal 1 publicando solo
Vídeo largo 16:9 con capítulos y miniaturas (formato principal), detector de historias, juez, títulos y descripciones con avisos, publicación con Upload-Post, planificador, límites de gasto y Telegram (avisos, veto y resumen semanal).

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
