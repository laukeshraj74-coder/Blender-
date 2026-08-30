# AI Video Generator - Packaging Guide

## Phase 5: Production Packaging

### Architecture Overview

```
Electron Desktop UI (frontend)
        ↓
Python Flask Backend (backend/)
        ↓
AI Service → Blender → FFmpeg → Final MP4
```

### How Backend Starts

1. Electron main process starts automatically when app launches
2. `startBackend()` spawns Python process with `main.py`
3. Backend runs on `http://127.0.0.1:5000`
4. Electron waits for health check endpoint before enabling UI
5. On shutdown, backend receives SIGTERM then SIGKILL if needed

### How Blender is Discovered

1. **Configured path**: User-specified path in Settings
2. **Common Windows paths**: 
   - `C:\Program Files\Blender Foundation\Blender 4.2\blender.exe`
   - `C:\Program Files\Blender Foundation\Blender 4.0\blender.exe`
   - `C:\Program Files\Blender Foundation\Blender 3.6\blender.exe`
3. **System PATH**: Searches for `blender` or `blender.exe`

### How FFmpeg is Discovered

1. **Configured path**: User-specified path in Settings
2. **Common Windows paths**:
   - `C:\Program Files\FFmpeg\bin\ffmpeg.exe`
   - `C:\Program Files (x86)\FFmpeg\bin\ffmpeg.exe`
   - `C:\ffmpeg\bin\ffmpeg.exe`
3. **System PATH**: Searches for `ffmpeg` or `ffmpeg.exe`

### Where User Projects are Stored

Projects are stored in the user's application data directory:
- **Windows**: `%APPDATA%\AIVideoGenerator\projects\`
- **Linux**: `~/.local/share/AIVideoGenerator/projects/`
- **macOS**: `~/Library/Application Support/AIVideoGenerator/projects/`

### How Configuration is Stored

Configuration file location:
- **Windows**: `%APPDATA%\AIVideoGenerator\config.json`
- **Linux**: `~/.local/share/AIVideoGenerator/config.json`
- **macOS**: `~/Library/Application Support/AIVideoGenerator/config.json`

### Build Commands

**Development mode:**
```bash
npm run dev
```

**Build Windows installer:**
```bash
npm run build:win
```

### Generated Artifacts

After running `npm run build:win`:
- `dist/AI Video Generator Setup.exe` - NSIS installer

### Manual Tests Required on Windows

1. **Application Launch**: Double-click .exe, verify UI appears
2. **Backend Connection**: Check "Connected" status in UI
3. **Settings Persistence**: Configure API key, restart app, verify saved
4. **Blender Detection**: Install Blender, verify detection in Settings
5. **FFmpeg Detection**: Install FFmpeg, verify detection in Settings
6. **Video Generation**: Create project with prompt, generate video
7. **Output Validation**: Verify MP4 plays correctly
8. **Process Cleanup**: Close app, verify no orphan processes

### Limitations

- Python must be installed on target system (or bundle with PyInstaller)
- Blender and FFmpeg must be installed separately by user
- Icon placeholder needs replacement with proper .ico file

### Security Notes

- No hardcoded API keys
- No secrets in source code
- Path traversal protection in file uploads
- CORS enabled only for localhost
- Context isolation enabled in Electron
