# AI Video Generator

A professional desktop application for AI-powered video generation.

## Requirements

- Node.js 18+
- Python 3.9+
- FFmpeg (optional, for video processing)
- Blender (optional, for 3D rendering)

## Installation

### 1. Install Frontend Dependencies

```bash
npm install
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Run in Development Mode

From the project root:

```bash
npm start
```

This will start both the backend server and the Electron frontend.

## Project Structure

```
project/
│
├── frontend/          # Electron frontend
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── pages/         # Application pages
│   │   ├── styles/        # CSS styles
│   │   ├── utils/         # Utility functions
│   │   └── main.js        # Electron main process
│   └── assets/        # Static assets
│
├── backend/           # Python backend
│   ├── main.py            # Entry point
│   ├── config/            # Configuration management
│   ├── ai/                # AI provider integration
│   ├── blender/           # Blender integration
│   ├── video/             # Video processing
│   ├── audio/             # Audio/TTS processing
│   ├── projects/          # Project management
│   └── utils/             # Utilities
│
├── scripts/           # Build and utility scripts
├── tests/             # Test files
├── package.json       # Node.js configuration
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## Architecture

- **Frontend**: Electron with HTML/CSS/JavaScript
- **Backend**: Python with local IPC communication
- **Communication**: Local HTTP server (simple and debuggable)

## Features (Phase 1)

- Professional dark-themed UI
- Prompt composition with attachments
- Settings management (AI, Blender, FFmpeg)
- Project/history foundation
- Generation activity tracking
- Clean error handling

## License

MIT
