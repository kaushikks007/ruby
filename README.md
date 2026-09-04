# Ruby — Personal AI Assistant & Companion

Ruby is a personal AI assistant built for **kaushik**, designed to run locally on Windows with persistent memory, real-time voice, PC control, browser automation, and proactive check-ins.

---

## Current Status: Phases 1–6 Completed

> **Note:** The wake-word microphone bug (RMS stuck near-zero) was root-caused and
> fixed — Ruby was auto-selecting Windows' virtual "Primary Sound Capture Driver"
> (digital silence) and requesting 2 channels on a 4-channel array mic (dead
> channels). See `ruby/voice/audio_input.py` (live device probing).

### Phase 1 — The Brain
- [x] **Persistent Memory System (`memory/`)**:
  - `profile.json` — Preferences, routines, known contacts, voice choice.
  - `daily_log/YYYY-MM-DD.md` — Session summaries, mood/check-ins, milestones.
  - `projects/*.md` — Active hackathon and project context tracking.
  - `face_embeddings/` & `voice_embeddings/` — Initialized for biometric integration.
- [x] **Live Web Search & Fetch Tool (`ruby/tools/web_search.py`)**:
  - Direct live search (`ddgs` / fallback HTML parser) returning formatted snippets, URLs, and timestamps.
  - Webpage content reader (`fetch_webpage`).
- [x] **Dynamic Memory Context Assembly (`ruby/memory_manager.py`)**:
  - Injects active profile, contacts, recent daily logs, and project notes seamlessly into the system prompt.
- [x] **Claude Orchestration Loop (`ruby/brain.py`)**:
  - Multi-step tool use support (executes tools, returns results, continues reasoning).
  - Plain-language error reporting.

### Phase 2 — The Voice
- [x] **Local Whisper STT (`ruby/voice/stt.py`)**:
  - Powered by `faster-whisper` (CTranslate2) for offline, privacy-first transcription.
  - Integrated Voice Activity Detection (VAD) with energy-based silence detection.
- [x] **TTS Engine & Voice Catalog (`ruby/voice/tts.py`)**:
  - High-quality neural voices via `edge-tts` (`ruby-warm` Aria, `ruby-conversational` Jenny, `ruby-chai` Neerja, `ruby-crisp` Sonia, `ruby-male` Guy) + offline Windows SAPI5 (`pyttsx3`).
  - Markdown-to-speech cleaner.
- [x] **Wake-Word Engine (`ruby/voice/wake_word.py`)**:
  - Listens for **"Hey Ruby"** to wake up the assistant.
- [x] **Voice Customizer & Setup (`ruby/voice/voice_selector.py`)**:
  - Preview voice samples and switch default voice in `memory/profile.json`.
- [x] **Unified Voice Loop (`ruby/voice/voice_assistant.py`)**:
  - Wake Word ("Hey Ruby") → Listen/Transcribe → Brain Reasoning & Tools → Spoken Response.

### Phase 3 — The Body (Browser & WhatsApp Automation)
- [x] **Persistent Browser Controller (`ruby/browser/browser_manager.py`)**:
  - Playwright controller using local Google Chrome with persistent session state stored in `browser_data/` (keeps WhatsApp Web login and cookies saved).
- [x] **WhatsApp Web Automation (`ruby/browser/whatsapp.py`)**:
  - "send a WhatsApp message to X saying Y" flow: opens Chrome, navigates to WhatsApp Web, searches contact, types message, and prompts for confirmation.
  - **Confirm-Before-Send Safeguard**: Displays preview and pauses for user confirmation before hitting send.
  - **Plain-Language Diagnostics**: Clearly explains if a QR scan is required, if a contact name couldn't be found, or if a network glitch occurred.
- [x] **Browser Tools (`ruby/tools/browser_tools.py`)**:
  - Tools for Claude: `send_whatsapp_message`, `browse_url`, `capture_page_screenshot`.

### Phase 4 — The Body (OS-level Control)
- [x] **Application Launcher (`ruby/os_control/app_launcher.py`)**:
  - Launches desktop applications (VS Code, Notepad, Calculator, Chrome, Spotify, Terminal, Settings, Explorer, etc.) with PID tracking.
  - One-line plan narration before launching.
- [x] **Scoped Memory File System (`ruby/os_control/file_ops.py`)**:
  - Strictly scoped to `C:\Users\sudha\OneDrive\ruby\memory\`.
  - Directory traversal protection (blocks attempts to escape memory root).
  - Destructive action confirmation on file deletion.
- [x] **Script Execution Engine (`ruby/os_control/script_runner.py`)**:
  - Runs Python (`.py`), PowerShell (`.ps1`), and Batch (`.bat`) scripts located in `scripts/`.
  - Potentially destructive command detector enforcing user confirmation.
- [x] **OS Tools (`ruby/tools/os_tools.py`)**:
  - `launch_app`, `read_memory_file`, `write_memory_file`, `delete_memory_file`, `execute_script`.

### Phase 5 — The Face (Face Recognition)
- [x] **Local Face Recognition (`ruby/face/`)**:
  - Webcam capture (`camera.py`), Haar-cascade detection (`detector.py`), secure-folder enrollment (`enroll.py`), and an LBPH recognizer (`recognizer.py`) trained from enrolled samples — all on-device, no cloud.
  - Enrolled face crops + trained model stored in `memory/face_embeddings/`.
  - **FaceGuard (`face_guard.py`)** confirms it's really the owner (several consecutive matching frames) and is wired into the voice loop to gate commands.
  - CLI: `scripts/face_enroll.py` (enroll the owner) and `scripts/face_verify_live.py` (live test).
  - First-run requires the Haar cascade at `ruby/face/data/haarcascade_frontalface_default.xml` (bundled).

### Phase 6 — The Avatar (3D Overlay)
- [x] **3D Spider Avatar (`ruby/avatar/`)**:
  - Three.js spider model with an idle motion loop; reacts (subtle animation change) to `idle` / `listening` / `speaking`.
  - Electron always-on-top, transparent, frameless overlay window (`main.js`, `package.json`).
  - `AvatarStateServer` (`bridge.py`) drives state from Python over localhost; the voice loop sets it and the avatar animates while Ruby listens/speaks.
  - Run standalone: `.\.venv\Scripts\python.exe scripts\avatar.py`
- [x] **Setup**: `pip install -r requirements.txt` then `cd ruby/avatar && npm install` (downloads Electron + Three.js).

---

## Quick Start

### 1. Configure API Key
Create or edit `.env` in `C:\Users\sudha\OneDrive\ruby\.env`:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### 2. Run Modes

**Chat CLI Mode:**
```powershell
.\.venv\Scripts\python.exe main.py
```

**Voice Wake-Word Mode ("Hey Ruby"):**
```powershell
.\.venv\Scripts\python.exe main.py --voice
```

**Voice Customizer / Preview:**
```powershell
.\.venv\Scripts\python.exe main.py --voices
```

### 3. CLI Commands
- `/open <app>` — Launch an application (e.g. `notepad`, `calc`, `vscode`, `chrome`)
- `/read <file>` — Read a memory file (e.g. `projects/hackathon.md`)
- `/write <file> <content>` — Create or update a file in memory
- `/run <script>` — Run a script from `scripts/` (e.g. `system_status.py`)
- `/whatsapp <contact> <message>` — Send WhatsApp message with confirmation preview
- `/browse <url>` — Browse a page and summarize content
- `/screenshot` — Take screenshot of current browser window
- `/voice` — Enter wake-word voice assistant mode
- `/voices` — Voice selector tool
- `/profile`, `/memory`, `/projects`, `/search <query>`, `/clear`, `exit`

### 4. Run Automated Tests
```powershell
.\.venv\Scripts\python.exe -m pytest tests/
```
> Tests are isolated automatically by `tests/conftest.py`: they run against a
> throwaway temp data root (`RUBY_DATA_ROOT`), so they never write into your real
> `memory/` folder.
