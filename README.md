# Agente Académico

Sistema agéntico de inteligencia artificial desarrollado para la actividad **"P1 – Construcción del sistema agéntico"** de la asignatura **Sistemas Agénticos y Orquestadores de IA** (Unidad 2: Orquestación Basada en Cadenas) — Universidad Católica Luis Amigó.

El agente es un asistente académico que conversa con el estudiante, mantiene memoria de la conversación, actualiza el estado del estudiante (nombre, programa, semestre) y puede consultar el horario de clases mediante una herramienta (function calling).

## Demo desplegada

🔗 [https://sistema-agentico-1.onrender.com](https://sistema-agentico-1.onrender.com)

## Arquitectura

El proyecto sigue una orquestación basada en cadenas: cada mensaje del usuario pasa por una secuencia de pasos (captura → actualización de estado → construcción de contexto → llamada al modelo → uso de herramienta si aplica → respuesta), implementada sobre **Streamlit** como interfaz y **Gemini** como modelo de lenguaje.

```
sistema_agentico/
├── app.py                  # Interfaz Streamlit (entrada principal)
├── config/
│   └── settings.py         # Carga de variables de entorno y validación de configuración
├── core/
│   ├── agent.py             # Lógica del agente: contexto, instrucciones y llamada a Gemini
│   └── state.py             # Estado de sesión: datos del estudiante, historial y memoria
├── tools/
│   └── horario_tool.py      # Herramienta de function calling: consulta de horarios
├── data/
│   └── horarios.json        # Datos de horario académico usados por la herramienta
├── requirements.txt
└── render.yaml               # Configuración de despliegue en Render
```

**Componentes principales:**

- **Modelo:** Gemini (`gemini-2.5-flash`), a través del SDK `google-genai`.
- **Instrucciones del agente:** definidas dinámicamente en `core/agent.py`, combinan el estado actual del estudiante y la memoria reciente de la conversación como contexto del sistema.
- **Manejo de información:** `core/state.py` guarda en `st.session_state` los datos del estudiante y el historial de mensajes, y construye la memoria conversacional que se envía al modelo en cada turno.
- **Herramienta:** `consultar_horario` (en `tools/horario_tool.py`) permite al agente buscar clases por día o asignatura en `data/horarios.json` cuando el estudiante pregunta por horarios.

## Ejecutar en local

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/LogicaLio/sistema_agentico.git
   cd sistema_agentico
   ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Crear un archivo `.env` en la raíz del proyecto con tu API Key de Gemini:
   ```
   GEMINI_API_KEY=tu_api_key_aqui
   ```
   (Se puede generar una API Key gratuita en [Google AI Studio](https://aistudio.google.com/)).

4. Ejecutar la aplicación:
   ```bash
   streamlit run app.py
   ```

5. Abrir el navegador en `http://localhost:8501`.

## Despliegue

El proyecto está configurado para desplegarse en **Render** mediante `render.yaml`:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
- **Variable de entorno requerida:** `GEMINI_API_KEY` (configurada como secreta en el dashboard de Render).

## Ejemplo de uso

```
Usuario: Hola, soy Sebas, estudio Ingeniería de Sistemas, voy en tercer semestre. ¿Qué clases tengo el lunes?

Agente: Hola, Sebas. Los lunes tienes las siguientes clases:
- Bases de Datos: 8:00 a. m. - 10:00 a. m. (Aula 301)
- Programación: 10:00 a. m. - 12:00 m. (Laboratorio 2)
```

## Autor

Proyecto desarrollado para la asignatura Sistemas Agénticos y Orquestadores de IA — Docente: Alvaro Pérez Niño.
