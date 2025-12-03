# Testing Tools Reference

Additional tools for automation and demos.

---

## xdotool - Keyboard/Mouse Simulation

```bash
# Type text
xdotool type "Hello World"

# Press keys
xdotool key Return
xdotool key Tab
xdotool key ctrl+c

# Mouse
xdotool mousemove 100 200
xdotool click 1  # Left click
xdotool click 3  # Right click
```

---

## wmctrl - Window Control

```bash
# List windows
wmctrl -l

# Focus window by title
wmctrl -a "LocaNext"

# Move/resize window
wmctrl -r "LocaNext" -e 0,0,0,1920,1080
```

---

## xclip - Clipboard

```bash
# Copy to clipboard
echo "text" | xclip -selection clipboard

# Paste from clipboard
xclip -selection clipboard -o
```

---

## ffmpeg - Screen Recording

```bash
# Record 60 seconds
ffmpeg -f x11grab -video_size 1920x1080 -framerate 30 -i :0 \
  -c:v libx264 -preset ultrafast -t 60 demo.mp4

# Record specific window (get geometry first)
xdotool getactivewindow getwindowgeometry
```

---

## scrot - Quick Screenshots

```bash
# Full screen
scrot screenshot.png

# Delayed (3 seconds)
scrot -d 3 screenshot.png

# Active window only
scrot -u window.png
```

---

## ImageMagick - Screenshot with Selection

```bash
# Click to select area
import screenshot.png
```

---

## Summary Table

| Tool | Purpose | Example |
|------|---------|---------|
| xdotool | Keyboard/mouse | `xdotool type "test"` |
| wmctrl | Window control | `wmctrl -l` |
| xclip | Clipboard | `echo "x" \| xclip` |
| ffmpeg | Video recording | `ffmpeg -f x11grab...` |
| scrot | Screenshots | `scrot shot.png` |
