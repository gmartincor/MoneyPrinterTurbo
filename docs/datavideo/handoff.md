# Punto de partida: estado, siguientes pasos y cuentas

Este documento es la memoria del proyecto entre sesiones. Claude Code lo lee al empezar (lo exige `CLAUDE.md`) y lo actualiza al terminar cada sesión de trabajo: **Estado actual** y **Siguientes pasos** deben reflejar siempre la realidad del repositorio.

Arquitectura confirmada: [`architecture.md`](architecture.md).

---

## 1. Estado actual

Última actualización: **3 de noviembre de 2026**, rama `main`.

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

- Perfil creado: `channels/tu_dinero_es.toml` (falta el `voice_id` de ElevenLabs).
- Pruebas: `uv run --no-sync python -X utf8 -m pytest -q test/services/test_datavideo_*.py` → todas pasan.
- La batería completa del proyecto tiene 9 fallos **heredados del proyecto original** en pruebas de audio con Python 3.13 (`test_remote_speech_complete_decode`, `test_webui_bgm`, `test_webui_custom_audio_upload`, `test_bgm_decoded_audio`). Ya fallaban antes de este trabajo; no tocarlos salvo que se decida arreglarlos aparte.

**Pendiente de bloqueo externo:**
- La sesión en la nube no tenía acceso de red a las fuentes de datos ni a ElevenLabs/OpenAI. **En local no hay ese problema.**
- Faltan las cuentas y claves de la sección 3.

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
5. Crea un archivo `.env` en la raíz (ya está en `.gitignore`, **nunca se sube**) con las claves de la sección 3, una por línea, por ejemplo `OPENAI_API_KEY=...`. Para ejecutar con esas claves:
   ```bash
   uv run --env-file .env --no-sync python -X utf8 -m pytest -q test/services/test_datavideo_*.py
   ```
6. Abre la carpeta en VS Code. Claude Code carga `CLAUDE.md`, que le indica leer las skills, este documento y la arquitectura antes de trabajar. Pídele: *"Sigue con los siguientes pasos de docs/datavideo/handoff.md"*.
7. Para traer mejoras del proyecto original (una vez):
   ```bash
   git remote add upstream https://github.com/harry0703/MoneyPrinterTurbo.git
   ```

**Nunca pegues claves en el chat.** Van solo en `.env` o en las variables del servidor.

---

## 3. Cuentas y claves, en orden

| # | Servicio | Para qué | Qué hacer | Coste | Variable | Cuándo |
|---|---|---|---|---|---|---|
| 1 | **OpenAI Platform** | Guionista y juez (GPT-6.1 Sol) | Crear clave de API y **poner un límite de gasto mensual** (p. ej. 20 $) | ~3–10 $/mes | `OPENAI_API_KEY` | H1 |
| 2 | **ElevenLabs** (cuenta **separada** de la de tus agentes) | Voz | Plan **Creator**. Crear con **Voice Design** una voz en español peninsular para *Tu Dinero en Datos* y copiar su `voice_id` en `channels/tu_dinero_es.toml` | ~22 $/mes | `ELEVENLABS_API_KEY` | H1 |
| 3 | **Google / YouTube** | Canales | Verificación en dos pasos. Crear un **canal de pruebas** (privado) y la cuenta de marca *Tu Dinero en Datos* | 0 € | — | H1 (pruebas), H2 |
| 4 | **Google Cloud** | API de YouTube | Proyecto nuevo; activar *YouTube Data API v3* y *YouTube Analytics API*; pantalla de consentimiento OAuth en **Producción** (nunca *Testing*); cliente OAuth de escritorio; **solicitar la auditoría** de la API (tarda semanas, empezar pronto) | 0 € | `GOOGLE_OAUTH_CLIENT_FILE` (ruta al JSON) | H2 |
| 5 | **Instagram + Facebook** | Reels y carruseles | Cuenta profesional de Instagram y página de Facebook por canal, conectadas entre sí | 0 € | — | H2 |
| 6 | **Upload-Post** | Publicar | Plan de pago; un perfil por canal con YouTube, Instagram y Facebook conectados | ~16 $/mes | `UPLOAD_POST_API_KEY` | H2 |
| 7 | **Telegram** | Avisos y veto | Crear bot con @BotFather y obtener tu `chat_id` | 0 € | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | H2 |
| 8 | **Datos España** | Canal 1 | REE (apidatos.ree.es), Ministerio (carburantes), INE, Banco de España: sin registro | 0 € | — | H1 |
| 9 | **Datos EE. UU.** | Canal 2 | Registro gratuito en BLS, EIA y FRED | 0 € | `BLS_API_KEY`, `EIA_API_KEY`, `FRED_API_KEY` | H4 |
| 10 | **Datos mundo** | Canal 3 | Banco Mundial, Eurostat, Our World in Data: sin registro | 0 € | — | H5 |
| 11 | **NASA** | Canal 4 | Clave gratuita en api.nasa.gov | 0 € | `NASA_API_KEY` | H5 |
| 12 | **Servidor** | Funcionar 24/7 | VPS de 4 núcleos y 8 GB (o tu PC encendido) | ~10 €/mes | — | H2 |
| 13 | **Amazon Afiliados** (ES y US) | Ingresos por afiliación | Alta en ambos programas | 0 € | — | H3 |
| 14 | **AdSense + W-8BEN** | Cobrar de YouTube | Vincular al pedir el Programa de Partners; rellenar el formulario fiscal de EE. UU. | 0 € | — | Al acercarse a 1.000 suscriptores |
| 15 | **Gestor fiscal** | Hacienda | Consultar **antes del primer ingreso**: alta censal, autónomo (tarifa plana en torno a 80 €/mes el primer año) e IRPF | — | — | Antes de cobrar |
| 16 | **Dominio + Cloudflare Pages** | Web de datos | Registrar dominio y crear el proyecto | ~1 €/mes | `CLOUDFLARE_API_TOKEN` | H5 |

---

## 4. Licencias pendientes de verificar

Una fuente solo puede usarse en un vídeo publicado cuando su `Source.license_verified` es `True`. Revisar y anotar la licencia exacta en el código de cada fuente:

- REE REData, Ministerio (carburantes), INE, Banco de España (ojo: el Euríbor diario tiene restricciones de EMMI; usar el dato mensual oficial).
- Eurostat, Banco Mundial (CC BY 4.0 según su catálogo), Our World in Data.
- NASA (sin derechos de autor en general, sin usar su logo; hay excepciones de terceros), ESA/Webb (CC BY 4.0).
- BLS, EIA, FRED (algunas series de FRED son de terceros con restricciones).
- Mapas: Natural Earth (dominio público), IGN/CNIG (CC BY 4.0).
- Fuente tipográfica BeVietnamPro (OFL) y biblioteca de música elegida.

---

## 5. Siguientes pasos

### H1 — Primer Short real, en privado

| # | Tarea | Aceptación | Verificación |
|---|---|---|---|
| 1 | `sources/ree.py`: precios PVPC del día siguiente | Cliente con timeout y validación; respuesta real guardada como fixture; produce `HourlyPrice`; licencia verificada | Prueba de contrato con la fixture |
| 2 | `speech.py`: texto hablado es-ES/en-US | "0,082 €/kWh", "14:00", "181 %" y fechas se convierten a palabras correctas | Pruebas unitarias |
| 3 | `voice.py`: ElevenLabs con marcas de tiempo | Audio + alineación; caché por hash de texto, voz y modelo; cuenta caracteres para el presupuesto | Prueba con respuesta real guardada |
| 4 | `timeline.py` | Cada segmento con inicio y fin exactos; subtítulos por frase con el texto mostrado | Pruebas unitarias |
| 5 | Escenas `big_number` y `source_card` | Se ven bien en 9:16 y 16:9 | Imágenes de referencia + revisión visual |
| 6 | `render.py` | Short 9:16 con escenas, voz, subtítulos y volumen normalizado | Prueba de render corta |
| 7 | `store.py`, `pipeline.py`, `cli.py dry-run` | Ejecución completa para `tu_dinero_es` sin publicar, reanudable | Simulación de principio a fin |
| 8 | Banco de pruebas de guiones | 20 casos; comparar GPT-6.1 Sol y Terra; anotar resultado en `architecture.md` | Informe del banco |

**Fin de H1:** un Short generado con datos reales de hoy, verificado, con voz, revisado por el propietario y subido en **privado** al canal de pruebas.

### H2 — Canal 1 publicando solo
Detector de historias, juez, títulos y descripciones con avisos, publicación con Upload-Post, planificador, límites de gasto y Telegram (avisos, veto y resumen semanal).

### H3 — Vídeo largo
Formato 16:9, capítulos, miniaturas, fuentes de Euríbor e IPC, estadísticas, afiliados.

### H4 — Aprendizaje y canal 2
Bucle de estadísticas → pesos del juez; canal `your_money_us`.

### H5 — Canales 3 y 4 y web
`mundo_es`, `space_en` y la web de datos.

---

## 6. Previsión económica

Estimación propia, con mucha incertidumbre. Los ingresos dependen de que los canales enganchen, y eso no se puede saber antes de publicar.

**Costes:** ~50 €/mes con 1 canal; ~70–135 €/mes con 4 canales (según el precio final de la voz). Primer año: ~1.000–1.400 €.

**Requisito para cobrar anuncios:** 1.000 suscriptores y 4.000 horas de visualización en 12 meses por canal (equivale a unas 60.000 visitas de vídeos largos con ~4 minutos vistos de media). Puede subir a 8.000 horas desde febrero de 2027 (sin confirmar).

| Escenario | Qué pasa | Ingresos/mes al mes 12 | Margen/mes al mes 12 |
|---|---|---|---|
| Pesimista (el más probable) | Ningún canal o uno llega a monetizar | 0–50 € | −50 a −130 € → se pausan canales y se reduce el gasto |
| Base | 1–2 canales monetizados, 20.000–60.000 visitas largas/mes en total | 150–450 € | +50 a +350 € |
| Optimista | 3–4 canales monetizados y uno despega | 1.500–4.000 € | +1.400 a +3.800 € (a partir del mes 15–24) |

A esto hay que restar impuestos y, si corresponde, la cuota de autónomo (consultar al gestor).
