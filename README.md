# 🍕 San Francisco Crust Pizza — Sistema Inteligente de Apoyo a la Decisión

Dashboard ejecutivo en Streamlit con filtros dinámicos, análisis estratégico automático y asistente de IA.

## Estructura
```
app.py                 # Interfaz (sidebar, KPIs, gráficos, pestañas, chat)
src/data_loader.py     # Lectura CSV/XLSX, detección de columnas (ALIASES), unión y cálculo de ventas/costo/utilidad
src/metrics.py         # KPIs, agrupaciones y series temporales
src/charts.py          # Gráficos Plotly (barras, líneas, áreas, donas, mapa)
src/insights.py        # Hallazgos, mejor/peor sucursal, productos, segmento potencial, recomendaciones
src/assistant.py       # Chatbot (OpenAI o compatible) con fallback local sin API key
src/demo_data.py       # Datos sintéticos de demostración
data/                  # (opcional) archivos por defecto: nombres con "ventas", "clientes", "productos"
.streamlit/config.toml # Tema corporativo
```

## Datos
- Acepta **CSV o XLSX**. El nombre del archivo debe contener `ventas`, `clientes` o `productos`.
- Las tablas se unen por `id_cliente` e `id_producto` (nombres equivalentes se detectan solos; ver `ALIASES` en `src/data_loader.py`).
- Ventas = columna de ventas/total, o precio × cantidad. Costo = columna de costo, o costo unitario × cantidad.
- Si tus columnas usan otros nombres, añádelos a `ALIASES`. El panel lateral *Esquema detectado* muestra qué columna se asignó a cada campo.
- Para el mapa, incluye `latitud` y `longitud` en clientes o ventas; si no las hay, se usan las coordenadas de `COORDENADAS` en `src/charts.py` (ya incluye Dallas, Houston, Austin y San Antonio; añade otras ciudades ahí).
- Validado con los archivos reales: `ClienteID`, `ProductoID`, `VentaID`, `VentaNeta`, `CostoTotal` se detectan automáticamente.
- Sin archivos, la app muestra datos de demostración. Los archivos cargados con el *File Uploader* reemplazan a los de `data/` y todo se recalcula sin tocar el código.

## Ejecución local
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
IA generativa (opcional): define `OPENAI_API_KEY` como variable de entorno, en `.streamlit/secrets.toml` (ver `secrets.toml.example`) o pégala en el panel *Configuración de IA*. Sin key, el asistente responde con reglas locales.

## Despliegue gratuito en Streamlit Community Cloud
1. Crea una cuenta en https://github.com y un repositorio nuevo (**privado** si incluyes datos reales).
2. Sube el proyecto (`app.py`, `src/`, `requirements.txt`, `.streamlit/config.toml`, `README.md`). No subas `secrets.toml`.
   ```bash
   git init && git add . && git commit -m "SF Crust Pizza" 
   git branch -M main && git remote add origin https://github.com/TU_USUARIO/TU_REPO.git && git push -u origin main
   ```
3. Entra en https://share.streamlit.io, inicia sesión con GitHub y pulsa **Create app → Deploy a public app from GitHub**.
4. Elige repositorio, rama `main` y archivo principal `app.py` (si el repo es privado, autoriza el acceso).
5. En **Advanced settings → Secrets** pega: `OPENAI_API_KEY = "sk-..."`. Elige Python 3.11 o 3.12.
6. Pulsa **Deploy**. Cada `git push` actualiza la app automáticamente.

Notas: la app gratuita se "duerme" tras días sin uso y se reactiva al visitarla. Para datos sensibles, usa repositorio privado o carga los archivos con el uploader en lugar de subirlos a GitHub.
