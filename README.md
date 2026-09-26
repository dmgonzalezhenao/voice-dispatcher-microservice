# 🎙️ Voice AI Dispatcher Microservice

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Supabase](https://img.shields.io/badge/Supabase-CDN_Storage-3ECF8E?style=flat&logo=supabase&logoColor=white)](https://supabase.com/)
[![ElevenLabs](https://img.shields.io/badge/ElevenLabs-TTS_API-black?style=flat)](https://elevenlabs.io/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A high-performance asynchronous microservice engineered for batch Text-to-Speech (TTS) voice synthesis via **ElevenLabs API**, featuring parallel execution, dynamic concurrency control, and instant cloud persistence using **Supabase Storage CDN**.

---

## 💡 The Problem & The Solution

* **The Problem:** Processing large texts or multiple independent phrases through traditional sequential HTTP requests leads to severe latency bottlenecks and poor end-user experiences.
* **The Solution:** This microservice implements **non-blocking asynchronous concurrency** via `asyncio.gather` coupled with a execution semaphore. It dispatches text chunks in parallel and simultaneously uploads generated audio artifacts to the cloud, significantly reducing end-to-end response times.

---

## 🏗️ System Architecture

```text
+----------------------------+
                    |   Streamlit Cloud UI       |
                    |   (Frontend Client)        |
                    +--------------+-------------+
                                   |
                            HTTP POST /dispatch
                                   |
                                   v
                    +----------------------------+
                    |   Render Web Service       |
                    |   (FastAPI Backend)        |
                    +--------------+-------------+
                                   |
              +--------------------+--------------------+
              | (asyncio.gather)                        | (asyncio.gather)
              v                                         v
 +-------------------------+               +-------------------------+
 | ElevenLabs API          |               | Supabase Storage        |
 | (Throttled Semaphore 2) |               | (Cloud CDN Bucket)      |
 +-------------------------+               +-------------------------+
```

 ---

## ✨ Key Features

* **Asynchronous Batch Processing:** Parallel execution of multi-phrase voice synthesis using `httpx.AsyncClient` and `asyncio.gather`.
* **Throttled Concurrency ("Safe Synthesis"):** Strict concurrency limits using `asyncio.Semaphore(2)` to respect ElevenLabs free tier rate limits and prevent `429 Too Many Requests` errors.
* **Cloud Asset Persistence:** Automatic upload of synthesized audio to **Supabase Storage** with public CDN URL generation.
* **Security & Traffic Management:**
  * IP-based rate limiting via `slowapi` (restricted to 3 free requests/day per client IP).
  * Dynamic header override (`X-ElevenLabs-Key`), allowing users to provide their own API keys and bypass system quota limits.
  * Internal authentication middleware (`X-API-KEY`).
* **Modern Tooling:** Lightning-fast dependency management and virtual environment orchestration powered by `uv`.

---

## 🛠️ Tech Stack

* **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2, `slowapi`, `httpx`.
* **Frontend:** Streamlit.
* **Storage:** Supabase Storage (CDN).
* **AI Engine:** ElevenLabs Text-to-Speech API.
* **Tooling & Infrastructure:** `uv`, Render, Streamlit Community Cloud.

---

## 🚀 Local Installation & Setup

### 1. Prerequisites
Ensure you have [Python 3.11+](https://www.python.org/) and [uv](https://github.com/astral-sh/uv) installed.

```bash
# Install uv package manager if needed
pip install uv
```

### 2. Clone the Repository

```bash
git clone [https://github.com/your-username/voice-dispatcher-microservice.git](https://github.com/dmgonzalezhenao/voice-dispatcher-microservice.git)
cd voice-dispatcher-microservice
```

### 3. Install Dependencies

```bash
uv sync
```

### 4. Environment Variables (.env)
Create a .env file in the project root with the following configuration:

```properties
# Backend Security
API_SECRET_KEY=your_internal_api_secret_key

# ElevenLabs Credentials
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Supabase Storage Configuration
SUPABASE_URL=[https://your-project.supabase.co](https://your-project.supabase.co)
SUPABASE_KEY=your_supabase_service_role_or_anon_key
SUPABASE_BUCKET=audio-outputs

# Frontend Configuration
BACKEND_URL=[http://127.0.0.1:8000](http://127.0.0.1:8000)
```

## ⚡ Local Execution
### Run the Backend Service (FastAPI)

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

The server will start at [http://127.0.0.1:8000](http://127.0.0.1:8000). Access OpenAPI documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Run the Frontend Interface (Streamlit)
In a separate terminal session:

```bash
uv run streamlit run frontend/app.py
```

The interactive application will launch automatically at http://localhost:8501.

---

## 📡 API Reference
### GET /health
**Description:** Health check endpoint monitored by cloud platforms (Render/Railway).

* **Response (200 OK):**

```json
{
  "status": "healthy",
  "service": "voice-dispatcher-microservice"
}
```

### POST /api/v1/dispatch
* **Headers:**

  * X-API-KEY: System authorization key (required).
  * X-ElevenLabs-Key: User-provided ElevenLabs API key (optional, bypasses IP rate limit).

* **Request Body:**

```json
{
  "phrases": [
    "Hello, this is a batch voice dispatch test.",
    "Asynchronous execution significantly decreases latency."
  ],
  "voice_id": "pNInz6obpgDQGcFmaJgB",
  "delivery_mode": "cloud_url",
  "settings": {
    "stability": 0.5,
    "similarity_boost": 0.75  
  }
}
```

* **Response (200 OK):**

```json
{
  "status": "success",
  "total_processed": 2,
  "elapsed_time_seconds": 1.84,
  "results": [
    {
      "phrase": "Hello, this is a batch voice dispatch test.",
      "audio_data": "[https://your-project.supabase.co/storage/v1/object/public/audio-outputs/uuid1.mp3](https://your-project.supabase.co/storage/v1/object/public/audio-outputs/uuid1.mp3)"
    },
    {
      "phrase": "Asynchronous execution significantly decreases latency.",
      "audio_data": "[https://your-project.supabase.co/storage/v1/object/public/audio-outputs/uuid2.mp3](https://your-project.supabase.co/storage/v1/object/public/audio-outputs/uuid2.mp3)"
    }
  ]
}
```

---

## 🌐 Cloud Deployment
* **Backend:** Deployed to **Render** as a Web Service using a Procfile and uv sync --frozen build strategy.
* **Frontend:** Hosted on **Streamlit Community Cloud**, linked to the GitHub repository with configuration managed via Streamlit Secrets.

---

## 📄 License
Distributed under the MIT License.