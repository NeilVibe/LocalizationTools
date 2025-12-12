
import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import json

def get_program_dir():
    """Return the folder where the script/exe is located."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return Path(sys.executable).parent
    else:
        # Running as .py script
        return Path(__file__).parent

def get_file_size_mb(path):
    return os.path.getsize(path) / (1024 * 1024)

def get_video_height(path):
    """Use ffprobe to get the actual video height."""
    ffprobe_path = get_program_dir() / "ffprobe.exe"
    if not ffprobe_path.exists():
        messagebox.showerror("Error", f"ffprobe.exe not found in program folder:\n{ffprobe_path}")
        return None
    try:
        cmd = [
            str(ffprobe_path),
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=height",
            "-of", "json",
            path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return data["streams"][0]["height"]
    except Exception as e:
        messagebox.showerror("Error", f"Failed to get video resolution:\n{e}")
        return None

def predict_new_size_mb(original_size_mb, crf, resolution, original_height):
    """
    Prediction based on CRF and resolution scaling.
    CRF effect: CRF 18 ~ original size, CRF 28 ~ ~40% of original.
    Resolution effect: scale by pixel count ratio.
    """
    if crf < 18: crf = 18
    if crf > 28: crf = 28
    crf_ratio = 1.0 - ((crf - 18) / (28 - 18)) * 0.6  # from 100% down to ~40%

    # Resolution ratio based on actual height
    if resolution == "720p":
        res_ratio = (1280 * 720) / ((original_height * 16/9) * original_height)
    elif resolution == "540p":
        res_ratio = (960 * 540) / ((original_height * 16/9) * original_height)
    else:  # keep original
        res_ratio = 1.0

    return original_size_mb * crf_ratio * res_ratio

def downsize_video(input_file, crf, resolution):
    ffmpeg_path = get_program_dir() / "ffmpeg.exe"
    if not ffmpeg_path.exists():
        messagebox.showerror("Error", f"ffmpeg.exe not found in program folder:\n{ffmpeg_path}")
        return

    output_file = get_program_dir() / (Path(input_file).stem + "_small.mp4")

    # GPU NVENC settings
    vcodec = "h264_nvenc"
    rc_args = ["-cq", str(crf)]
    preset = "p1"

    # Resolution scaling
    scale_args = []
    if resolution == "720p":
        scale_args = ["-vf", "scale=-2:720"]
    elif resolution == "540p":
        scale_args = ["-vf", "scale=-2:540"]

    cmd = [
        str(ffmpeg_path),
        "-i", input_file,
        "-c:v", vcodec,
        *rc_args,
        "-preset", preset,
        *scale_args,
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_file)
    ]

    try:
        subprocess.run(cmd, check=True)
        messagebox.showinfo("Success", f"Downsized video saved:\n{output_file}")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"FFmpeg failed:\n{e}")

def select_file():
    path = filedialog.askopenfilename(title="Select MP4 Video", filetypes=[("MP4 files","*.mp4")])
    if not path:
        return
    selected_file.set(path)
    size_mb = get_file_size_mb(path)
    original_size_mb.set(f"{size_mb:.2f} MB")
    height = get_video_height(path)
    if height:
        original_height.set(height)
        predicted_size_mb.set(f"{predict_new_size_mb(size_mb, crf_value.get(), resolution_choice.get(), height):.2f} MB")

def update_prediction(val=None):
    if not selected_file.get():
        return
    size_mb = get_file_size_mb(selected_file.get())
    height = original_height.get()
    if height:
        predicted_size_mb.set(f"{predict_new_size_mb(size_mb, crf_value.get(), resolution_choice.get(), height):.2f} MB")

def start_downsize():
    if not selected_file.get():
        messagebox.showerror("Error", "Please select a video file first.")
        return
    downsize_video(selected_file.get(), crf_value.get(), resolution_choice.get())

# ——— GUI Setup ———
root = tk.Tk()
root.title("Video Downsizer (GPU NVENC Only)")

selected_file     = tk.StringVar()
original_size_mb  = tk.StringVar(value="N/A")
predicted_size_mb = tk.StringVar(value="N/A")
crf_value         = tk.IntVar(value=28)
resolution_choice = tk.StringVar(value="Original")
original_height   = tk.IntVar(value=1080)

tk.Button(root, text="Select MP4 File", command=select_file).pack(pady=5)

tk.Label(root, text="Selected File:").pack()
tk.Label(root, textvariable=selected_file, wraplength=400).pack()

tk.Label(root, text="Original Size:").pack()
tk.Label(root, textvariable=original_size_mb).pack()

tk.Label(root, text="Predicted New Size:").pack()
tk.Label(root, textvariable=predicted_size_mb).pack()

tk.Label(root, text="Quality (Lower CRF/QP = better quality, larger file)").pack()
tk.Scale(root,
         from_=18, to=28,
         orient="horizontal",
         variable=crf_value,
         command=lambda v: update_prediction()).pack()

tk.Label(root, text="Resolution:").pack()
tk.OptionMenu(root, resolution_choice, "Original", "720p", "540p", command=lambda _: update_prediction()).pack()

tk.Button(root, text="Downsize Video (GPU NVENC)", command=start_downsize).pack(pady=10)

root.mainloop()
