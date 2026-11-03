# Arquitectura del sistema de vídeos de datos

Estado: **confirmada por el propietario el 3 de noviembre de 2026**. Cualquier cambio de diseño se refleja aquí antes de implementarlo.

## 1. Objetivo

Producir y publicar sin intervención humana vídeos originales construidos a partir de datos oficiales y verificables, en varios canales (uno por perfil), maximizando ingresos y sin incumplir las normas de YouTube, Meta ni el Reglamento europeo de IA.

## 2. Decisiones de producto

| Tema | Decisión |
|---|---|
| Canales | 4, lanzados de forma escalonada: `tu_dinero_es` (finanzas del hogar, España, español), `your_money_us` (finanzas del hogar, EE. UU., inglés), `mundo_es` (el mundo en datos, español), `space_en` (espacio y ciencia, inglés) |
| Deportes | Descartados como canal principal: los datos de pago no incluyen derechos sobre las competiciones y el RPM es bajo. Posible experimento futuro con datos de dominio público de openfootball, sin imágenes de partidos |
| Formatos por canal | Shorts 3–5 por semana (solo si superan el listón), vídeo largo semanal de 8–12 min, vídeo largo de búsqueda cada 2 semanas, especiales por publicación de datos |
| Plataformas | YouTube (principal), Instagram Reels y carruseles, Facebook. TikTok solo alcance opcional |
| Imagen | Generada por nuestro código: gráficos, mapas, cifras. Imágenes reales de NASA/ESA en `space_en`. Sin modelos de generación de vídeo (Sora cerrado, Veo caro e impreciso con cifras) |
| Texto | GPT-6.1 Sol por API oficial de OpenAI para guionista y juez; configurable por rol en el perfil del canal. Se valida frente a GPT-6.1 Terra con un banco de pruebas |
| Voz | ElevenLabs Multilingual v2, una voz creada con Voice Design por canal. Cuenta separada de la de los agentes del propietario |
| Publicación | Upload-Post (integración del proyecto original) hasta pasar la auditoría de la API de YouTube y la configuración directa con Meta |
| Comentarios | Sin automatizar. Moderación con ajustes nativos de YouTube Studio e Instagram |
| Avisos | Fuente en pantalla y descripción; aviso de "guion generado con IA a partir de datos oficiales" (art. 50 del Reglamento de IA); aviso de afiliados |
| Datos | Solo fuentes con licencia que permita uso comercial. Cada fuente registra su licencia y si está verificada |

## 3. Decisiones técnicas

| # | Decisión | Estado |
|---|---|---|
| D1 | Datos con tipo: `Fact(key, statement, source, as_of)` y `Source(name, url, license, license_verified)` | ✅ `app/datavideo/facts.py` |
| D2 | Guion estructurado en JSON: título + segmentos con texto, claves de datos y escena; verificación por segmento | ✅ `app/datavideo/script.py` |
| D3 | Dos textos por segmento: el mostrado (cifras) y el hablado (normalizado por código para la voz) | ⏳ `speech.py` |
| D4 | Voz con marcas de tiempo por carácter (`/v1/text-to-speech/{voice_id}/with-timestamps`) para subtítulos y cortes de escena | ⏳ `voice.py` |
| D5 | Catálogo de escenas con interfaz común `draw(size, progress)`, renderizables en 9:16 y 16:9 | ✅ base + `hourly_prices`; ⏳ resto |
| D6 | Montaje propio por línea de tiempo, reutilizando utilidades del proyecto original (subtítulos, música, FFmpeg, Upload-Post) | ⏳ `timeline.py`, `render.py` |
| D7 | Perfil de canal en `channels/<id>.toml`, validado de forma estricta | ✅ `app/datavideo/channels.py` |
| D8 | Estado de cada ejecución en SQLite, pasos reanudables, publicación idempotente | ⏳ `store.py`, `pipeline.py` |
| D9 | Interfaz de publicación común; Upload-Post ahora, APIs directas después | ⏳ `publish/` |
| D10 | Límites de gasto mensuales por proveedor y canal | ⏳ `budget.py` |
| D11 | Copia de cada respuesta de las fuentes con su licencia, para auditoría y pruebas | ⏳ `sources/` |
| D12 | Avisos legales automáticos en descripción y pantalla | ⏳ `packaging.py` |

## 4. Flujo de un vídeo

```
Planificador (cada noche, por canal)
 1. Fuentes → copia de la respuesta + licencia → datos con tipo (D1, D11)
 2. Detector de historias (código): récords, cambios, rankings, comparaciones, calendario
 3. Juez (LLM + pesos aprendidos) → si nada supera el listón, no se publica
 4. Guion JSON (LLM): segmentos + datos + escena + título + descripción (D2)
 5. Verificador: cifras por segmento, título, longitud, escenas y datos existentes
 6. Texto hablado (D3) → voz con marcas de tiempo (D4)
 7. Línea de tiempo: cada segmento con su escena y su duración exacta
 8. Render: escenas + voz + subtítulos + música → 9:16 y/o 16:9, miniatura, capítulos (D5, D6)
 9. Controles técnicos: duración, volumen (-14 LUFS), fotogramas negros, metadatos
10. Publicación programada con veto opcional por Telegram (D9)
11. Estadísticas a 48 h y 7 días → pesos del juez, horarios, formatos
12. Avisos por Telegram: bloqueos, fallos, gasto, resumen semanal
```

## 5. Módulos

```
channels/<id>.toml                  perfiles de canal, sin secretos
app/datavideo/
  locale.py      ✅ formato de números, porcentajes y fechas (es-ES, en-US)
  facts.py       ✅ Fact, Source
  figures.py     ✅ verificación de cifras y números escritos con letra (es-ES, en-US)
  script.py      ✅ guion estructurado y verificado
  channels.py    ✅ perfiles de canal y generador de texto por rol
  theme.py       ✅ colores y tipografía
  scenes/        ✅ base.py (interfaz, render a clip), hourly_prices.py
  electricity.py ✅ resumen diario PVPC → datos
  sources/       ⏳ un cliente por fuente: ree, minetur_fuel, bde, ine, eurostat, worldbank, nasa, bls, eia, fred
  stories/       ⏳ detectores de historias
  judge.py       ⏳ juez con rúbrica + pesos aprendidos
  speech.py      ⏳ texto hablado (D3)
  voice.py       ⏳ ElevenLabs con marcas de tiempo + caché por hash
  timeline.py    ⏳ segmentos + marcas de tiempo → escenas con duración
  render.py      ⏳ composición final
  packaging.py   ⏳ título, descripción, etiquetas, capítulos, miniatura, avisos
  qa.py          ⏳ controles técnicos
  publish/       ⏳ interfaz + upload_post + youtube_api + meta_graph
  analytics.py   ⏳ ingesta de estadísticas
  learning.py    ⏳ ajuste de pesos
  budget.py      ⏳ control de gasto
  notify.py      ⏳ Telegram
  store.py       ⏳ SQLite
  pipeline.py    ⏳ orquestación reanudable
  cli.py         ⏳ produce | dry-run | publish | report
```

## 6. Contratos clave

**Respuesta del guionista (JSON):**
```json
{"title": "...", "segments": [{"text": "...", "facts": ["fact_key"], "scene": "scene_id"}]}
```
Reglas comprobadas por código: cada cifra de un segmento aparece en los datos que ese segmento cita; el título solo usa cifras de los datos; no hay números escritos con letra ni proporciones; claves y escenas existen; longitud total dentro del rango.

**Perfil de canal (campos actuales):** `id`, `name`, `language`, `[models] provider/writer/judge`, `[voice] provider/model/voice_id`, `[theme]` con colores y fuente. Campos previstos que se añadirán cuando exista el módulo que los usa: `sources`, `formats`, `schedule`, `publish`, `budget`, `disclosure`, `affiliates`.

## 7. Estrategia de pruebas

| Nivel | Qué | Dónde |
|---|---|---|
| Unitarias | Lógica pura | `test/services/test_datavideo_*.py` |
| Contrato | Cada fuente con respuestas reales guardadas como fixture | `test/services/fixtures/datavideo/` |
| Imagen | Escenas comparadas con imágenes de referencia | por escena |
| Guiones | 20 casos fijos: % que pasa el verificador a la primera y comparación ciega entre modelos | banco de pruebas |
| Simulación | Vídeo completo sin publicar | `cli dry-run` |
| Canal de pruebas | Subidas privadas antes de activar un canal | YouTube |

## 8. Costes previstos

| Concepto | 1 canal | 4 canales |
|---|---|---|
| ElevenLabs | Creator ~22 $/mes | Pro ~99 $/mes (o Creator con exceso hasta 3 canales) |
| GPT-6.1 Sol | ~3 $/mes | ~10 $/mes |
| Upload-Post | ~16 $/mes | ~16 $/mes (hasta pasar a APIs directas) |
| Servidor | ~10 €/mes | ~10–15 €/mes |
| Datos | 0 € | 0 € |
| Dominio | ~1 €/mes | ~1 €/mes |

Regla: solo se mejora un servicio cuando un canal lo justifica con datos, y un canal sin crecimiento a los 3 y 6 meses se pausa.
