# config.py - Global parameters for AirSign

# ── Camera ──────────────────────────────────────────────────────────────────
CAMERA_INDEX = 1          # 0 = default webcam, 1+ = OBS Virtual Camera / Kinect
FRAME_WIDTH  = 1280
FRAME_HEIGHT = 720
FPS_TARGET   = 30

# ── MediaPipe Hand Tracking ──────────────────────────────────────────────────
MP_MAX_HANDS             = 1
MP_MIN_DETECTION_CONF    = 0.7
MP_MIN_TRACKING_CONF     = 0.6

# ── Gesture thresholds ───────────────────────────────────────────────────────
FINGER_STRAIGHT_THRESHOLD = 0.6   # ratio used to decide if a finger is extended
PINCH_DISTANCE_THRESHOLD  = 40    # pixels: index-tip to thumb-tip for pinch

# ── Drawing ──────────────────────────────────────────────────────────────────
DRAW_COLOR        = (0, 255, 0)    # BGR green
ERASE_COLOR       = (0, 0, 0)      # BGR black
DRAW_THICKNESS    = 6
ERASER_RADIUS     = 30
CANVAS_BG_COLOR   = (0, 0, 0)      # black background canvas

# ── UI / Overlay ─────────────────────────────────────────────────────────────
TOOLBAR_HEIGHT    = 80             # pixels from top reserved for toolbar
BUTTON_COLOR      = (50, 50, 50)   # BGR default button
BUTTON_HOVER_COLOR= (80, 120, 200)
BUTTON_TEXT_COLOR = (255, 255, 255)
FONT_SCALE        = 0.7
FONT_THICKNESS    = 2

# ── OCR (TrOCR) ──────────────────────────────────────────────────────────────
TROCR_MODEL       = "microsoft/trocr-base-handwritten"

# ── TTS (pyttsx3) ────────────────────────────────────────────────────────────
TTS_RATE          = 160            # words per minute
TTS_VOLUME        = 1.0            # 0.0 – 1.0
TTS_VOICE_INDEX   = 0              # 0 = first available voice

# ── Export ───────────────────────────────────────────────────────────────────
# EXPORT_DIR is resolved to <project_root>/exports/ inside utils/image_exporter.py
EXPORT_PREFIX     = "airsign_canvas"
