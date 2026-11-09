# Arquitectura del sistema de vídeos de datos

Estado: **confirmada por el propietario el 3 de noviembre de 2026**, revisada el mismo día para reutilizar la voz, los subtítulos y el montaje del proyecto original. Cualquier cambio de diseño se refleja aquí antes de implementarlo.

## 1. Objetivo

Producir y publicar sin intervención humana vídeos originales construidos a partir de datos oficiales y verificables, en varios canales (uno por perfil), maximizando ingresos y sin incumplir las normas de YouTube, Meta ni el Reglamento europeo de IA.

**Nadie introduce temas.** El proyecto original necesita que alguien escriba un tema; este sistema lo elige solo: el detector de historias recorre los datos oficiales de cada canal, el juez elige la mejor historia y el guionista la escribe. La IA no busca en internet: así cada cifra es verificable y no hay contenido de terceros.

## 2. Decisiones de producto

| Tema | Decisión |
|---|---|
| Canales | 4, lanzados de forma escalonada: `tu_dinero_es` (*Tu Dinero en Datos*: finanzas del hogar, España, español), `your_money_us` (*The Wallet Census*: finanzas del hogar, EE. UU., inglés), `mundo_es` (*Medir el Mundo*: el mundo en datos, español), `space_en` (*The Apogee Almanac*: espacio y ciencia, inglés) |
| Deportes | Descartados como canal principal: los datos de pago no incluyen derechos sobre las competiciones y el RPM es bajo. Posible experimento futuro con datos de dominio público de openfootball, sin imágenes de partidos |
| Formatos por canal | El vídeo largo es el formato principal: semanal de 8–12 min con una pregunta, ranking y mapa; de búsqueda cada 2 semanas; especiales el día que se publica un dato oficial. Shorts 3–5 por semana (solo si superan el listón), con un dato de un vídeo largo para llevar a él |
| Datos del canal 1 | INE (CC BY 4.0) y Eurostat, ambos con uso comercial permitido sin autorización previa. REE queda descartada: su aviso legal limita la reutilización a fines no comerciales salvo autorización escrita, y un dato diario del precio de la luz caduca en 24 horas y repite el mismo formato |
| Plataformas | YouTube (principal), Instagram Reels y carruseles. Facebook descartado definitivamente. TikTok solo alcance opcional |
| Imagen | Generada por nuestro código: gráficos, mapas, cifras. Imágenes reales de NASA/ESA en `space_en`. Sin modelos de generación de vídeo (Sora cerrado, Veo caro e impreciso con cifras) |
| Texto | GPT-6.1 Sol por API oficial de OpenAI para guionista y juez; configurable por rol en el perfil del canal. Se valida frente a GPT-6.1 Terra con un banco de pruebas |
| Voz | Motor de voz del proyecto original, elegido por canal con `voice.name`. **Azure Speech oficial** (pago por uso, ~1–5 $/mes con los 4 canales) por defecto. **ElevenLabs** solo si las estadísticas demuestran que la voz frena la retención de un canal. **Edge TTS** solo para desarrollo: es gratis pero no es un servicio pensado para uso comercial |
| Publicación | Upload-Post (integración del proyecto original). Pasar a las APIs directas de YouTube o Meta es opcional. No se solicita la auditoría de la API de YouTube: solo sería obligatoria para superar 100 subidas al día |
| Comentarios | Sin automatizar. Moderación con ajustes nativos de YouTube Studio e Instagram |
| Avisos | Fuente en pantalla y descripción; aviso de "guion generado con IA a partir de datos oficiales" (art. 50 del Reglamento de IA); aviso de afiliados |
| Datos | Solo fuentes con licencia que permita uso comercial. Cada fuente registra su licencia y si está verificada |

## 3. Qué reutilizamos y qué es nuestro

| Pieza | Origen |
|---|---|
| Llamadas a modelos de texto (OpenAI y otros) | Proyecto original: `app/services/llm.py` (`_generate_response`) |
| Voz con tiempos por palabra (Azure, ElevenLabs, Edge…) | Proyecto original: `app/services/voice.py` (`tts` devuelve `SubMaker`) |
| Subtítulos con estilo | Proyecto original: `app/services/task.py` (`generate_subtitle`) y `subtitle.py` |
| Música, unión de clips y vídeo final con FFmpeg | Proyecto original: `task.generate_final_videos` y `video.py` |
| Publicación | Proyecto original: `app/services/upload_post.py` |
| Datos, detector de historias, juez, guion verificado, escenas, planificador, estado, gasto, avisos | **Nuestro**: `app/datavideo/` |

## 4. Decisiones técnicas

| # | Decisión | Estado |
|---|---|---|
| D1 | Datos con tipo: `Fact(key, statement, source, as_of)` y `Source(name, url, license, license_verified)` | ✅ `app/datavideo/facts.py` |
| D2 | Guion estructurado en JSON: título + segmentos con texto, claves de datos y escena; verificación por segmento | ✅ `app/datavideo/script.py` |
| D3 | Un solo texto por segmento, el mismo para la voz y los subtítulos. Azure Speech en es-ES lee bien cifras con coma decimal, "%" y fechas; los datos se redactan con unidades en palabras ("puntos", "euros"). Un normalizador (`speech.py`) solo se añadirá cuando una fuente traiga unidades que la voz lea mal | Aplazado |
| D4 | Voz y tiempos por palabra con `voice.tts` del proyecto original en una sola síntesis de toda la narración. Cada palabra se alinea con su segmento comparando solo letras y dígitos; el corte entre segmentos cae entre la última palabra de uno y la primera del siguiente | ⏳ `timeline.py` |
| D5 | Catálogo de escenas con interfaz común `draw(size, progress)`, renderizables en 9:16 y 16:9. Las escenas dibujan los datos de la historia, nunca texto del modelo, y dejan libre el tercio inferior para los subtítulos | ✅ base; ⏳ `ranking`, `big_number`, `source_card` |
| D6 | Montaje: nuestro código genera una única pista de escenas sin audio, con la duración exacta de la voz. `voice.create_subtitle` y `video.generate_video` del proyecto original añaden subtítulos, voz y, cuando haya licencia, música. No se usa `task.generate_final_videos`, porque corta y baraja los clips de material | ⏳ `render.py` |
| D7 | Perfil de canal en `channels/<id>.toml`, validado de forma estricta | ✅ `app/datavideo/channels.py` |
| D8 | Cada ejecución tiene su carpeta (`storage/datavideo/<canal>/<historia>/`) con un artefacto por paso: respuesta de la fuente, datos, guion, audio, subtítulos, vídeo y resultado de publicación. Un paso se salta si su artefacto ya existe (reanudable) y una historia ya publicada no se vuelve a publicar (idempotente). SQLite solo si se necesitan consultas entre ejecuciones | ⏳ `store.py`, `pipeline.py` |
| D9 | Interfaz de publicación común; Upload-Post ahora, APIs directas después | ⏳ `publish/` |
| D10 | Límites de gasto mensuales por proveedor y canal | ⏳ `budget.py` |
| D11 | Copia de cada respuesta de las fuentes con su licencia, para auditoría y pruebas | ⏳ `sources/` |
| D12 | Avisos legales automáticos en descripción y pantalla | ⏳ `packaging.py` |

## 5. Flujo de un vídeo

```
Planificador (cada noche, por canal) — sin tema de entrada
 1. Fuentes → copia de la respuesta + licencia → datos con tipo (D1, D11)
 2. Detector de historias (código): récords, cambios, rankings, comparaciones, calendario
 3. Juez (LLM + pesos aprendidos) → si nada supera el listón, no se publica
 4. Guion JSON (LLM): segmentos + datos + escena + título + descripción (D2)
 5. Verificador: cifras por segmento, título, longitud, escenas y datos existentes
 6. voice.tts del proyecto original → audio + tiempos por palabra (D3, D4)
 7. Línea de tiempo: cada segmento con su escena y su duración exacta
 8. Pista de escenas → voice.create_subtitle + video.generate_video del proyecto original: subtítulos, voz, música (D5, D6)
 9. Controles técnicos: duración, volumen (-14 LUFS), fotogramas negros, metadatos
10. Publicación programada con veto opcional por Telegram (D9)
11. Estadísticas a 48 h y 7 días → pesos del juez, horarios, formatos
12. Avisos por Telegram: bloqueos, fallos, gasto, resumen semanal
```

## 6. Módulos

```
channels/<id>.toml                  perfiles de canal, sin secretos
app/datavideo/
  locale.py      ✅ formato de números, porcentajes y fechas (es-ES, en-US)
  facts.py       ✅ Fact, Source
  figures.py     ✅ verificación de cifras y números escritos con letra (es-ES, en-US)
  script.py      ✅ guion estructurado y verificado
  channels.py    ✅ perfiles de canal y generador de texto por rol
  theme.py       ✅ colores y tipografía
  scenes/        ✅ base.py (interfaz, render a clip); ⏳ ranking, big_number, source_card
  sources/       ⏳ un cliente por fuente: ine (primero), eurostat, worldbank, nasa, bls, eia, fred; minetur_fuel y bde solo si se verifica su licencia
  stories/       ⏳ detectores de historias: regional_ranking (primero)
  judge.py       ⏳ juez con rúbrica + pesos aprendidos (cuando haya varias historias candidatas)
  timeline.py    ⏳ voz, tiempos por palabra → segmentos con inicio y fin, subtítulos
  render.py      ⏳ pista de escenas + montaje del proyecto original
  packaging.py   ⏳ título, descripción, etiquetas, capítulos, miniatura, avisos
  qa.py          ⏳ controles técnicos
  publish.py     ⏳ Upload-Post con la cuenta del perfil del canal (clave desde .env)
  analytics.py   ⏳ ingesta de estadísticas
  learning.py    ⏳ ajuste de pesos
  budget.py      ⏳ control de gasto
  notify.py      ⏳ Telegram
  store.py       ⏳ carpeta por ejecución, artefactos por paso
  pipeline.py    ⏳ orquestación reanudable
  cli.py         ⏳ produce | publish
```

## 7. Contratos clave

**Respuesta del guionista (JSON):**
```json
{"title": "...", "segments": [{"text": "...", "facts": ["fact_key"], "scene": "scene_id"}]}
```
Reglas comprobadas por código: cada cifra de un segmento aparece en los datos que ese segmento cita; el título solo usa cifras de los datos; no hay números escritos con letra ni proporciones; claves y escenas existen; longitud total dentro del rango.

**Perfil de canal (campos actuales):** `id`, `name`, `language`, `[models] provider/writer/judge`, `[voice] name/rate` (nombre de voz en el formato del proyecto original: `es-ES-TristanMultilingualNeural-V2-Male` para Azure oficial (sufijo `-V2` antes del género), `elevenlabs:<voice_id>` para ElevenLabs, `es-ES-AlvaroNeural-Male` para Edge en desarrollo), `[theme]` con colores y fuente. Campos previstos que se añadirán cuando exista el módulo que los usa: `sources`, `formats`, `schedule`, `publish`, `budget`, `disclosure`, `affiliates`.

## 8. Estrategia de pruebas

| Nivel | Qué | Dónde |
|---|---|---|
| Unitarias | Lógica pura | `test/services/test_datavideo_*.py` (~2 s en total) |
| Contrato | Cada fuente con respuestas reales guardadas como fixture | `test/services/fixtures/datavideo/` |
| Imagen | Escenas comparadas con imágenes de referencia | por escena |
| Guiones | 20 casos fijos: % que pasa el verificador a la primera y comparación ciega entre modelos | banco de pruebas |
| Simulación | Vídeo completo sin publicar | `cli dry-run` |
| Canal de pruebas | Subidas privadas antes de activar un canal | YouTube |

**Ciclo de desarrollo:** en cada cambio se ejecutan solo las pruebas de `datavideo` y el lint (segundos). En GitHub Actions, `datavideo.yml` ejecuta esas pruebas cuando cambia nuestro código, y la batería completa del proyecto original (`ci.yml`, ~3.200 pruebas, ~14 min) solo cuando cambia código del proyecto original o se lanza a mano (tras traer cambios del original). No se borran esas pruebas: protegen el motor original del que dependemos (voz, subtítulos, montaje, publicación) y borrarlas causaría conflictos al traer actualizaciones.

## 9. Costes previstos

| Concepto | 1 canal | 4 canales |
|---|---|---|
| Voz (Azure Speech, pago por uso) | ~1–2 $/mes | ~4–5 $/mes |
| GPT-6.1 Sol | ~3 $/mes | ~10 $/mes |
| Upload-Post | ~16 $/mes | ~16 $/mes (hasta pasar a APIs directas) |
| Servidor | ~10 €/mes | ~10–15 €/mes |
| Datos | 0 € | 0 € |
| Dominio | ~1 €/mes | ~1 €/mes |
| **Total** | **~30 €/mes** | **~40–50 €/mes** |

ElevenLabs (22–99 $/mes) solo se añade a un canal si sus estadísticas lo justifican. Regla general: solo se mejora un servicio cuando un canal lo justifica con datos, y un canal sin crecimiento a los 3 y 6 meses se pausa.
