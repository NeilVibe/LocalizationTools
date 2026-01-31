# MapDataGenerator - Work In Progress

> Last updated: 2026-01-30

## Current Status: Build 015

**Working:**
- XML parsing with QACompilerNEW pattern (recover=True)
- DDS image display (~48% entries have images)
- Multi-language search (13 languages)
- Column toggles (Description OFF by default)
- Full 3D position display (X, Y, Z)

---

## TODO List

### High Priority

- [ ] **Cell expansion / auto-expand rows**
  - Long descriptions get truncated
  - QuickSearch-style: click to expand/collapse
  - Or: tooltip on hover showing full text

- [ ] **WEM audio player**
  - Play Wwise audio files (.wem) directly in app
  - Approach: vgmstream-cli.exe → WAV → Python audio playback
  - See research notes below

### Medium Priority

- [ ] **Better grid styling**
  - Row height adjustments
  - Text wrapping in cells
  - Alternating row colors

- [ ] **Mode-specific column defaults**
  - MAP: Position ON, Group OFF
  - CHARACTER: Group ON, Position OFF
  - ITEM: Group ON, Position OFF

### Low Priority

- [ ] **Export results**
  - Export search results to CSV/Excel

- [ ] **Batch image export**
  - Export all DDS images to PNG folder

- [ ] **Remember column preferences**
  - Save toggle states to settings

---

## WEM Audio Player - Research Notes

### What is WEM?
WEM = Wwise Encoded Media. Audio format used by Wwise game audio engine.
Can contain: Vorbis, Opus, PCM, ADPCM audio.

### Approach (Recommended)

```
User clicks "Play" on WEM file
       ↓
vgmstream-cli.exe converts WEM → WAV (temp file)
       ↓
Python plays WAV (pygame / simpleaudio / winsound)
       ↓
Cleanup temp file
```

### Required Components

1. **vgmstream-cli.exe** (~2MB)
   - Download from: https://github.com/vgmstream/vgmstream/releases
   - Bundle with app or download on first use

2. **Python audio library** (choose one):
   - `pygame.mixer` - cross-platform, good for games
   - `simpleaudio` - lightweight, WAV only
   - `winsound` - Windows built-in, no dependencies

### Implementation Steps

```python
import subprocess
import tempfile
from pathlib import Path

def play_wem(wem_path: Path, vgmstream_path: Path):
    """Convert WEM to WAV and play."""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        wav_path = tmp.name

    # Convert WEM → WAV
    subprocess.run([
        str(vgmstream_path),
        '-o', wav_path,
        str(wem_path)
    ], check=True)

    # Play WAV
    import winsound
    winsound.PlaySound(wav_path, winsound.SND_FILENAME)

    # Cleanup
    Path(wav_path).unlink()
```

### Alternative: wwiser (Python)
- https://github.com/bnnm/wwiser
- Pure Python Wwise .bnk explorer
- More complex, needs .bnk files not just .wem

### Sources
- [vgmstream](https://github.com/vgmstream/vgmstream)
- [wwiser](https://github.com/bnnm/wwiser)
- [Wwise Audio Unpacker](https://github.com/f1ac/Wwise-Audio-Unpacker)

---

## Completed (Build History)

### Build 015 (2026-01-30)
- [x] Column toggle checkboxes
- [x] Description OFF by default
- [x] Full 3D position (X, Y, Z)

### Build 014 (2026-01-30)
- [x] QACompilerNEW XML pattern
- [x] Fixed DDS lookup (UITextureName corruption)

### Build 013 (2026-01-29)
- [x] XML sanitizer unterminated attribute fix

### Build 012 (2026-01-29)
- [x] DDS diagnostic report

### Build 011 (2026-01-29)
- [x] Fixed double-processing bug in MAP mode
