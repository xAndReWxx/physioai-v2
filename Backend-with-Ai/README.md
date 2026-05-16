# 🏥 PhysioAI Pro V2 — Backend

> Realtime AI-powered physiotherapy posture tracking system.

A production-grade FastAPI backend for streaming camera frames via WebSocket, processing them through an AI pipeline, and returning realtime pose analysis with posture scoring and coaching feedback.

---

## 🏗️ Architecture

```
backend/
│
├── app/
│   ├── main.py                    # FastAPI application factory
│   ├── config/
│   │   └── settings.py            # Pydantic Settings (env-based config)
│   ├── core/
│   │   ├── events.py              # Startup/shutdown lifecycle
│   │   └── exceptions.py          # Custom exception hierarchy
│   ├── models/
│   │   └── packets.py             # Pydantic WebSocket packet models
│   ├── websocket/
│   │   ├── manager.py             # Connection manager (multi-client)
│   │   └── handler.py             # WebSocket message handler
│   ├── services/
│   │   ├── ai_engine.py           # AI processing engine (placeholder)
│   │   ├── frame_router.py        # Frame routing + rate limiting
│   │   └── posture_analyzer.py    # Posture analysis (placeholder)
│   ├── middleware/
│   │   └── error_handler.py       # Global HTTP error handling
│   ├── routers/
│   │   ├── health.py              # Health check endpoints
│   │   └── websocket_routes.py    # WebSocket route definitions
│   └── utils/
│       ├── logger.py              # Structured logging (structlog)
│       └── helpers.py             # Utility functions
│
├── tests/
│   ├── test_health.py             # Health endpoint tests
│   ├── test_websocket.py          # WebSocket lifecycle tests
│   └── test_packets.py            # Pydantic model tests
│
├── .env                           # Environment config (DO NOT COMMIT)
├── .env.example                   # Config template
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Pytest configuration
└── README.md                      # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy the template
cp .env.example .env

# Edit .env with your settings (defaults work for development)
```

### 4. Run the Server

```bash
# Development (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Verify

- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **WebSocket:** ws://localhost:8000/ws/pose

---

## 📡 WebSocket Protocol

### Endpoint

```
ws://localhost:8000/ws/pose
```

### Connection Flow

1. Client connects → Server sends welcome message with config
2. Client sends frame packets → Server responds with pose results
3. Client can send heartbeat packets to keep connection alive
4. Either side can close the connection

### Client → Server

#### Frame Packet

```json
{
  "type": "frame",
  "timestamp": 1710000000.123,
  "frame": "<base64_encoded_jpeg>"
}
```

#### Heartbeat Packet

```json
{
  "type": "heartbeat",
  "timestamp": 1710000000.123
}
```

### Server → Client

#### Welcome (on connect)

```json
{
  "type": "connected",
  "client_id": "client_a1b2c3d4",
  "config": {
    "max_fps": 25,
    "target_fps": 20,
    "max_frame_size": 524288,
    "heartbeat_interval": 30
  },
  "message": "Connected to PhysioAI Pro V2"
}
```

#### Pose Result

```json
{
  "type": "pose_result",
  "fps": 20,
  "landmarks": [
    { "x": 0.5, "y": 0.15, "z": 0.0, "visibility": 0.95 }
  ],
  "posture_score": 88,
  "feedback": "Keep your back straight",
  "latency_ms": 25,
  "exercise_data": null
}
```

#### Error

```json
{
  "type": "error",
  "code": "FRAME_VALIDATION_ERROR",
  "message": "Frame size 1.2 MB exceeds maximum 512.0 KB"
}
```

---

## 🧪 Running Tests

```bash
pytest -v
```

---

## ⚙️ Configuration

All settings are configurable via environment variables (`.env` file):

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Environment mode |
| `DEBUG` | `true` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server bind port |
| `WS_MAX_CONNECTIONS` | `50` | Max simultaneous WebSocket connections |
| `WS_HEARTBEAT_INTERVAL` | `30` | Heartbeat interval (seconds) |
| `MAX_FPS` | `25` | Maximum frames per second to process |
| `TARGET_FPS` | `20` | Target FPS in responses |
| `MAX_FRAME_SIZE_BYTES` | `524288` | Max frame size (512KB) |
| `CORS_ORIGINS` | `localhost:3000,...` | Allowed CORS origins |
| `LOG_LEVEL` | `DEBUG` | Logging level |
| `LOG_FORMAT` | `console` | Log format (console/json) |

---

## 🔮 Future Integration

The architecture is prepared for:

- **MediaPipe** pose estimation (swap `ai_engine.py` internals)
- **Posture analysis** algorithms (implement `posture_analyzer.py`)
- **Exercise tracking** with rep counting
- **Arabic voice coaching** text generation
- **Multi-exercise support** via frame router

See the commented integration code in `app/services/ai_engine.py` for MediaPipe setup.

---

## 📋 HTTP Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Server info |
| `GET` | `/health` | Detailed health status |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/docs` | Swagger UI (dev only) |
| `WS` | `/ws/pose` | Pose streaming endpoint |

---

## ⚡ Performance Notes

- **Single worker recommended** for WebSocket (stateful connections)
- Rate limiting enforces `MAX_FPS` per client
- `asyncio.Semaphore` limits concurrent AI processing
- Frames are dropped under load to preserve latency
- All I/O is async — no blocking operations
