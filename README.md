# 🤖 Furby Connect Web Controller

A comprehensive web-based control interface for **Furby Connect** toys, featuring Bluetooth LE communication, voice commands, and AI-powered conversations. Test in simulation mode without hardware, or connect to a real Furby for full control.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ Features

- 🔌 **Bluetooth LE Control** - Direct BLE communication with Furby Connect via [PyFluff](https://github.com/martinwoodward/PyFluff)
- 🎨 **Antenna Color Control** - Full RGB color customization (0-255)
- 🎭 **90+ Actions** - Comprehensive library of Furby behaviors (pet, tickle, sing, dance, etc.)
- 🎲 **Random Actions** - Surprise your Furby with unpredictable behaviors
- 🎤 **Voice Wake Word Detection** - Trigger actions with voice commands (Porcupine)
- 🤖 **OpenAI Integration** - Have real conversations with your Furby (Whisper + GPT-4o + TTS)
- 🎵 **Audio Playback** - Upload and play custom WAV files
- 🧪 **Simulation Mode** - Test everything without physical hardware
- 📱 **Web Interface** - Clean, intuitive browser-based control panel
- 📊 **Real-time Logging** - Monitor all operations and debug issues

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (required for PyFluff)
- **Furby Connect toy** (optional - simulation mode available)
- **Bluetooth-enabled device** (macOS, Linux, or Raspberry Pi)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/furby-web.git
cd furby-web

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings (see Configuration section)

# Run the application
uvicorn app:app --reload
```

Open your browser to **http://localhost:8000**

---

## 📁 Project Structure

```
furby-web/
├── app.py                      # Main FastAPI application
├── audio_converter.py          # Audio processing utilities
├── requirements.txt            # Python dependencies
├── .env.example               # Environment configuration template
├── scan_state.json            # BLE scan state persistence
├── silent_candidates.json     # Audio processing cache
├── test_microphone.py         # Microphone testing utility
│
├── 📚 Documentation
│   ├── README.md              # This file
│   ├── OPENAI_SETUP.md        # OpenAI conversation setup guide
│   ├── WAKE_WORD_SETUP.md     # Voice control configuration
│   ├── TROUBLESHOOTING.md     # Common issues and solutions
│   └── CHANGELOG.md           # Version history
│
└── 📱 iOS App (Optional)
    └── furby-ios/             # Native iOS Swift app
        ├── README.md
        ├── SETUP_GUIDE.md
        └── FurbyApp/          # Swift source files
```

---

## ⚙️ Configuration

Create a `.env` file in the project root (copy from `.env.example`):

```ini
# ===== Basic Settings =====
MOCK_MODE=true                    # true=simulation, false=real Furby
FURBY_ADDRESS=                    # Optional: Furby MAC address (AA:BB:CC:DD:EE:FF)
PORT=8000                         # Web server port

# ===== Wake Word Detection (Optional) =====
PORCUPINE_ENABLED=false           # Enable voice wake word detection
PORCUPINE_ACCESS_KEY=             # Get free key from https://console.picovoice.ai/
PORCUPINE_KEYWORD=alexa           # Wake word: alexa, jarvis, computer, etc.

# ===== OpenAI Conversation (Optional) =====
OPENAI_ENABLED=false              # Enable AI conversations
OPENAI_API_KEY=                   # Your OpenAI API key (sk-...)
CONVERSATION_TIMEOUT=5            # Recording duration in seconds
```

### Configuration Modes

| Mode | Use Case | Setup Required |
|------|----------|----------------|
| **Simulation** | Testing without Furby | None - works out of the box |
| **Basic BLE** | Control real Furby | Set `MOCK_MODE=false`, turn on Furby |
| **Voice Control** | Wake word triggers | Add Picovoice key, enable Porcupine |
| **AI Conversations** | Talk with Furby | Add OpenAI key, enable conversations |

---

## 🎮 Usage

### 1. Simulation Mode (No Hardware Required)

Perfect for testing, development, or just exploring the interface:

```bash
# Ensure MOCK_MODE=true in .env
uvicorn app:app --reload
```

- Scan shows simulated Furby devices
- All actions log to console
- Great for UI development

### 2. Real Furby Control

```bash
# Set MOCK_MODE=false in .env
# Turn on your Furby Connect
uvicorn app:app --reload
```

1. Click **"Scan"** to find nearby Furbies
2. Select your Furby from the list
3. Click **"Connect"**
4. Use controls to change colors, trigger actions, etc.

### 3. Voice Wake Word Control

Enable voice commands to trigger random Furby actions:

1. Get free access key from [Picovoice Console](https://console.picovoice.ai/)
2. Configure in `.env`:
   ```ini
   PORCUPINE_ENABLED=true
   PORCUPINE_ACCESS_KEY=your_key_here
   PORCUPINE_KEYWORD=alexa
   ```
3. Start detector in web interface (Section 5)
4. Say "Alexa" (or your chosen wake word)
5. Furby performs random action!

📖 **Full guide:** [WAKE_WORD_SETUP.md](./WAKE_WORD_SETUP.md)

### 4. OpenAI Conversations

Have actual conversations with your Furby using GPT-4:

1. Get OpenAI API key from [platform.openai.com](https://platform.openai.com/)
2. Configure in `.env`:
   ```ini
   OPENAI_ENABLED=true
   OPENAI_API_KEY=sk-your_key_here
   ```
3. Say wake word, then ask a question
4. Furby responds with AI-generated speech!

📖 **Full guide:** [OPENAI_SETUP.md](./OPENAI_SETUP.md)

---

## 🎨 Web Interface Overview

The control panel includes:

1. **Connection Panel** - Scan, connect, and manage BLE connection
2. **Antenna Control** - RGB sliders and color presets
3. **Action Triggers** - Send specific commands (input/index/subindex/specific)
4. **Audio Upload** - Play custom WAV files on Furby
5. **Random Actions** - Trigger surprise behaviors
6. **Wake Word Detection** - Voice control status and controls
7. **Live Log** - Real-time event monitoring

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### Setting Up Development Environment

```bash
# Fork and clone the repo
git clone https://github.com/YOUR_USERNAME/furby-web.git
cd furby-web

# Create a branch for your feature
git checkout -b feature/amazing-feature

# Make your changes and test thoroughly
python test_microphone.py  # Test audio features
uvicorn app:app --reload   # Test web interface

# Commit with clear messages
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
```

### Code Style

- Follow PEP 8 for Python code
- Add docstrings to new functions/classes
- Test in both simulation and real modes
- Update documentation for new features

### Areas We'd Love Help With

- [ ] Unit tests and integration tests
- [ ] Additional Furby action discovery
- [ ] UI/UX improvements
- [ ] Cross-platform compatibility (Windows)
- [ ] Docker containerization
- [ ] Additional language translations
- [ ] Better error handling and recovery
- [ ] Performance optimizations

---

## 🐛 Troubleshooting

### Common Issues

**"PyFluff import error"**
- Ensure Python 3.11+ is installed
- Try: `pip install --upgrade git+https://github.com/martinwoodward/PyFluff.git`

**"Furby not found in scan"**
- Make sure Furby is powered on (eyes open)
- Try turning Bluetooth off/on on your computer
- Move closer to Furby (within 2 meters)
- Ensure Furby isn't connected to another device

**"Port already in use"**
- Change `PORT=8000` to `PORT=8001` in `.env`
- Or find and kill the process: `lsof -ti:8000 | xargs kill`

**"Microphone not working"**
- macOS: Grant microphone permission in System Preferences → Security & Privacy
- Linux: Install `portaudio19-dev` and `python3-pyaudio`
- Test with: `python test_microphone.py`

**"Wake word not detected"**
- Check logs for volume levels (should be 200+)
- Try easier words first: "porcupine" or "jarvis"
- Speak clearly at normal volume
- See detailed guide: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

## 📚 Documentation

- **[OPENAI_SETUP.md](./OPENAI_SETUP.md)** - Complete OpenAI conversation setup
- **[WAKE_WORD_SETUP.md](./WAKE_WORD_SETUP.md)** - Voice control configuration
- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Detailed problem-solving guide
- **[CHANGELOG.md](./CHANGELOG.md)** - Version history and updates
- **[furby-ios/](./furby-ios/)** - Native iOS app documentation

---

## 🔧 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | FastAPI | Web server and REST API |
| **BLE Library** | Bleak | Cross-platform Bluetooth LE |
| **Furby Protocol** | PyFluff | Furby Connect communication |
| **Wake Word** | Porcupine | Voice wake word detection |
| **Speech-to-Text** | OpenAI Whisper | Transcribe audio to text |
| **AI Chat** | OpenAI GPT-4o-mini | Generate Furby responses |
| **Text-to-Speech** | OpenAI TTS | Convert responses to audio |
| **Audio Processing** | PyAudio, pydub | Microphone capture and playback |
| **Frontend** | HTML/JavaScript | Web interface (inline in app.py) |

---

## 📱 iOS App

A native iOS Swift app is also available in the `furby-ios/` directory:

- Full feature parity with web version
- Native iOS UI with SwiftUI
- CoreBluetooth for BLE
- Speech Framework for voice control
- No backend required - runs entirely on device

See [furby-ios/README.md](./furby-ios/README.md) for setup instructions.

---

## 🎯 Roadmap

Future enhancements we're considering:

- [ ] Docker container for easy deployment
- [ ] Raspberry Pi auto-start configuration
- [ ] Multiple Furby support
- [ ] Action recording and playback
- [ ] Scheduled actions (alarm clock mode)
- [ ] Web-based action discovery tool
- [ ] REST API documentation with OpenAPI
- [ ] WebSocket support for real-time updates
- [ ] Mobile-responsive web interface
- [ ] Plugin system for custom actions

---

## 🙏 Credits & Acknowledgments

- **[PyFluff](https://github.com/martinwoodward/PyFluff)** - Furby Connect Python library by [@martinwoodward](https://github.com/martinwoodward)
- **[Porcupine](https://picovoice.ai/)** - On-device wake word detection by Picovoice
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework
- **[Bleak](https://github.com/hbldh/bleak)** - Cross-platform BLE library
- **Furby Community** - For reverse engineering the Furby Connect protocol

Special thanks to all contributors who have helped improve this project!

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Note:** This is an unofficial, community-created project. Furby and Furby Connect are trademarks of Hasbro, Inc.

---

## 🐛 Issues & Support

- **Found a bug?** [Open an issue](https://github.com/yourusername/furby-web/issues)
- **Have a question?** Check [Discussions](https://github.com/yourusername/furby-web/discussions)
- **Want to contribute?** See [Contributing](#-contributing) section above

---

## 🌟 Show Your Support

If you find this project useful, please:
- ⭐ Star the repository
- 🐛 Report bugs you find
- 💡 Suggest new features
- 🔀 Fork and contribute
- 📢 Share with other Furby enthusiasts!

---

**Built with 💜 for the Furby community**

*Happy Furby hacking! 🤖*
