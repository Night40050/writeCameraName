# ✋ AirSign

**AirSign** es una aplicación Python que convierte tus gestos de mano en dibujo aéreo, reconoce lo que escribiste con OCR y lo lee en voz alta.

Captura video desde la **OBS Virtual Camera** (compatible con Kinect Xbox 360), detecta la mano con **MediaPipe**, permite dibujar en el aire con el dedo índice y procesa el canvas con **TrOCR** (OCR) y **pyttsx3** (TTS).

---

## 📐 Arquitectura del proyecto

```
airsign/
├── main.py                   ← Punto de entrada y bucle principal
├── config.py                 ← Parámetros globales (cámara, colores, umbrales)
├── requirements.txt          ← Dependencias Python
├── setup_env.bat             ← Script de instalación del entorno virtual (Windows)
│
├── core/
│   ├── hand_tracker.py       ← Wrapper de MediaPipe Hands → landmarks + frame anotado
│   ├── canvas_manager.py     ← Canvas off-screen: dibujar, borrar, mezclar con cámara
│   └── gesture_classifier.py ← Clasifica gestos: DRAW, ERASE, SELECT, SCROLL, IDLE
│
├── ui/
│   ├── toolbar.py            ← Barra de botones: Save, Clear, Read, Speak
│   └── overlay.py            ← Composita capas: cámara + canvas + HUD + FPS
│
├── ai/
│   ├── ocr_engine.py         ← TrOCR con preprocesado de imagen → texto
│   └── tts_engine.py         ← pyttsx3 con multiprocessing (sin bug de silencio)
│
├── utils/
│   ├── image_exporter.py     ← Guarda PNG y TXT en airsign/exports/
│   └── obs_helper.py         ← Detecta índices de cámara disponibles
│
└── exports/                  ← Carpeta de salidas (se crea automáticamente)
    ├── airsign_canvas_*.png
    └── recognized_text.txt
```

---

## ⚙️ Flujo de funcionamiento

```
Cámara (OBS / Kinect)
        │
        ▼
   HandTracker.process()
   MediaPipe Hands
        │ landmarks 21 puntos
        ▼
GestureClassifier.classify()
        │
   ┌────┴────────────────┐
   │                     │
DRAW (☝)             ERASE (✌)
CanvasManager.draw() CanvasManager.erase()
        │
        ▼
   CanvasManager.blend()    ← mezcla canvas + frame
        │
        ▼
   Toolbar.render()         ← dibuja botones encima
        │
        ▼
   Overlay.compose()        ← HUD: gesto, FPS, status
        │
        ▼
   cv2.imshow("AirSign")
```

### Acción READ / puño ✊

```
on_read()
  ├── export_canvas()        → PNG guardado en exports/
  ├── OCREngine.recognise()
  │     ├── preprocesar: escala de grises → umbral → invertir → padding → resize
  │     └── TrOCR inferencia
  ├── append_ocr_result()    → línea con timestamp en recognized_text.txt
  ├── TTSEngine.speak()      → nuevo proceso pyttsx3 (sin bug de silencio)
  └── overlay.set_status()   → "Saved: Carlos  [airsign_canvas_*.png]"
```

---

## 🖐️ Gestos reconocidos

| Gesto | Dedos extendidos | Acción |
|-------|-----------------|--------|
| ☝ DRAW | Solo índice | Dibuja en el canvas |
| ✌ ERASE | Índice + medio | Borra con círculo |
| ✊ SELECT | Ninguno (puño) | Activa READ o hace clic en botón |
| 🖐 SCROLL | Los cinco | Reservado (pan/scroll futuro) |
| — IDLE | Cualquier otro | Sin acción |

---

## ⌨️ Atajos de teclado

| Tecla | Acción |
|-------|--------|
| `C` | Limpiar canvas |
| `S` | Guardar PNG del canvas |
| `R` | Ejecutar OCR + TTS + exportar |
| `P` | Repetir el último texto reconocido |
| `Q` / `Esc` | Salir |

---

## 🔧 Instalación

### Requisitos previos

- Python 3.10 o superior
- [OBS Studio](https://obsproject.com/) con Virtual Camera activada
- (Opcional) [KinectToVR](https://github.com/KinectToVR/KinectToVR) para Kinect Xbox 360

### Paso 1 – Crear entorno virtual e instalar dependencias

```bat
cd airsign
setup_env.bat
```

Esto crea `.venv/` e instala todos los paquetes de `requirements.txt`.

### Paso 2 – Activar el entorno (cada vez que abras una terminal nueva)

```bat
.venv\Scripts\activate
```

### Paso 3 – Detectar el índice de la cámara OBS

```bat
python utils/obs_helper.py
```

Ejemplo de salida:
```
Found cameras: [0, 1, 2]
Camera 1 OK — frame size: 1280x720
```

### Paso 4 – Configurar el índice de cámara

Edita [`config.py`](config.py) y establece el valor correcto:

```python
CAMERA_INDEX = 1   # ← índice de OBS Virtual Camera
```

### Paso 5 – Ejecutar la aplicación

```bat
python main.py
```

---

## 📦 Dependencias principales

| Paquete | Versión mínima | Uso |
|---------|---------------|-----|
| `opencv-python` | 4.8 | Captura de video y dibujo |
| `mediapipe` | 0.10 | Detección de manos |
| `numpy` | 1.24 | Operaciones de imagen |
| `transformers` | 4.35 | TrOCR (OCR de escritura a mano) |
| `torch` | 2.0 | Motor de inferencia de TrOCR |
| `Pillow` | 10.0 | Conversión de imágenes para TrOCR |
| `pyttsx3` | 2.90 | Síntesis de voz (TTS offline) |

---

## 📁 Archivos exportados

Todos los archivos se guardan en `airsign/exports/` (se crea automáticamente):

| Archivo | Descripción |
|---------|-------------|
| `airsign_canvas_YYYYMMDD_HHMMSS.png` | Snapshot del canvas al ejecutar READ |
| `recognized_text.txt` | Log acumulativo con timestamps de cada reconocimiento |

Ejemplo de `recognized_text.txt`:
```
[2024-01-15 20:03:11] Carlos
[2024-01-15 20:05:44] Hola mundo
```

---

## 🛠️ Configuración avanzada (`config.py`)

| Parámetro | Valor por defecto | Descripción |
|-----------|------------------|-------------|
| `CAMERA_INDEX` | `1` | Índice de la cámara OBS |
| `FRAME_WIDTH` | `1280` | Ancho del frame |
| `FRAME_HEIGHT` | `720` | Alto del frame |
| `DRAW_COLOR` | `(0, 255, 0)` | Color de trazo (BGR verde) |
| `DRAW_THICKNESS` | `6` | Grosor del trazo en píxeles |
| `ERASER_RADIUS` | `30` | Radio del borrador en píxeles |
| `TROCR_MODEL` | `microsoft/trocr-base-handwritten` | Modelo OCR |
| `TTS_RATE` | `160` | Velocidad de lectura (palabras/min) |
| `MP_MIN_DETECTION_CONF` | `0.7` | Confianza mínima de detección de mano |

---

## 🐛 Problemas conocidos y soluciones

| Problema | Solución |
|----------|----------|
| TTS solo habla la primera vez | Resuelto usando `multiprocessing.Process` por cada llamada a `speak()` |
| OCR reconoce texto incorrecto | El canvas se preprocesa: escala de grises → umbral → inversión → padding → resize antes de enviar a TrOCR |
| La cámara no abre | Ejecutar `python utils/obs_helper.py` para ver los índices disponibles; actualizar `CAMERA_INDEX` en `config.py` |
| TrOCR tarda en arrancar | El modelo se carga de forma lazy en la primera llamada; considera llamar `ocr.load()` al iniciar la app |
