# Guía de entrega — P4 (no hace falta subir este archivo al repositorio)

Tiempo estimado: 40 a 60 minutos.

## Paso 1 — Integrar el código al repositorio (10 min)

```powershell
cd C:\ruta\a\sistema_agentico
git checkout -b p4-entrega
```

1. Descomprime `agente_p4.zip` y copia **todo su contenido** sobre tu repositorio, aceptando reemplazar archivos.
2. **Borra** `core/agent.py` y `core/state.py` si todavía existen (son de la v01).
3. **Reemplaza tus datos de ejemplo por los reales:**
   - `data/horarios.json` (tu horario real; la herramienta busca el día o la asignatura en cada entrada).
   - `data/actividades.json` y `data/calendario.json` (fechas reales del semestre).
   - `data/conocimiento/`: agrega tu reglamento u otros documentos (`.md`, `.txt` o `.pdf`).
4. Crea tu `.env` con una **API Key nueva** (la anterior se pegó en un chat; revócala en Google AI Studio):
   ```
   GEMINI_API_KEY=tu_clave_nueva
   GEMINI_MODEL=gemini-2.5-flash
   ```

## Paso 2 — Instalar y probar en tu equipo (10 min)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest -q          # deben pasar las 56 pruebas
streamlit run app.py
```

Haz estas preguntas en la app y verifica el recorrido en la pestaña **Grafo**:

| Pregunta | Debe pasar por |
|---|---|
| ¿Qué es un crédito académico? | enrutador ➔ nodo_conceptual |
| ¿Qué clases tengo el lunes? | agente ➔ herramientas ➔ agente |
| ¿Hoy tengo clase? | dos pasadas por herramientas |
| Prioriza mis actividades pendientes | priorizar_actividades |
| ¿Qué pasa si falto mucho a clases? | consultar_base_conocimiento (RAG) |

Prueba también la memoria: pregunta "¿qué clases tengo el lunes?" y después "¿y el viernes?".

## Paso 3 — Generar las evidencias con Gemini real (10 min)

Es lo más importante para la rúbrica: evidencia real, no solo simulada.

```powershell
python scripts/generar_evidencias.py --modo real
```

- Crea `evidencias/informe_pruebas_real.md` y `evidencias/metricas_real.csv`.
- Si algún escenario sale **⚠️ Revisar**, revisa qué hizo el agente. Eso es un hallazgo: anótalo en la fila
  **H6** (y siguientes) de `evidencias/hallazgos.md` con su acción correctiva, corrígelo y vuelve a correr
  el script para tener la verificación "después".
- Si aparece un error 429 (límite de solicitudes), espera un minuto y repite.

Vuelve a generar el informe cuando termines de anotar los hallazgos, porque el script los incluye.

## Paso 4 — Subir al repositorio (5 min)

```powershell
git add .
git status        # verifica que .env NO aparezca en la lista
git commit -m "P4: RAG, observabilidad, interfaz mejorada, pruebas y evidencias"
git push -u origin p4-entrega
```

Luego haz merge a `main` (en GitHub: Pull request ➔ Merge). Render redespliega solo cuando cambia `main`.

## Paso 5 — Desplegar en Render (10 min)

1. En Render, abre tu servicio `agente-academico` (o crea uno con **New ➔ Blueprint** apuntando al repo).
2. En **Environment** confirma `GEMINI_API_KEY` con tu clave nueva y `GEMINI_MODEL=gemini-2.5-flash`.
3. Espera el deploy (logs en **Logs**) hasta ver el servicio en estado *Live*.
4. Abre la URL pública y repite 3 preguntas del Paso 2: una conceptual, una con herramienta y una de RAG.
5. Pega la URL en el README (sección "Demo desplegada") y haz otro commit y push.

Si falla el build, revisa el log: lo más común es un error de dependencias (`requirements.txt`) o la
variable `GEMINI_API_KEY` sin configurar.

## Paso 6 — Entregar

1. **URL del repositorio:** `https://github.com/LogicaLio/sistema_agentico`
2. **URL del proyecto desplegado:** la de Render.

## Guion para la demostración (3 a 5 minutos)

1. **Interfaz:** muestra el diseño, las preguntas sugeridas y que se ve bien en el celular (reduce la ventana).
2. **Ruta conceptual:** "¿Qué es un crédito académico?" ➔ pestaña Grafo: no usó herramientas.
3. **Herramientas y ciclo ReAct:** "¿Hoy tengo clase?" ➔ dos herramientas encadenadas.
4. **RAG:** una pregunta sobre el reglamento ➔ cita la fuente. Pregunta algo que no esté en los documentos y
   muestra que responde que no encontró información en lugar de inventar.
5. **Memoria:** pregunta de seguimiento ("¿y el viernes?"). Luego "Nueva conversación" ➔ memoria vacía.
6. **Observabilidad:** pestaña Métricas (tokens, latencia, uso de herramientas) y descarga del CSV.
7. **Ajustes:** explica los hallazgos de `evidencias/hallazgos.md` y el resultado de la ventana de contexto.
8. **Error controlado:** si quieres mostrarlo, desconecta internet y pregunta algo: aparece un mensaje claro.
