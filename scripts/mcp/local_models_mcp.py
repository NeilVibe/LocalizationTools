#!/usr/bin/env python3
"""Local AI Models MCP Server — Z-Image Turbo (NF4) + future models.

Production-grade FastMCP server for local GPU-based AI generation.
Lazy-loads models on first call, unloads on idle to free VRAM.
Uses NF4 quantization to fit on RTX 4070 Ti 12GB VRAM (~5GB model footprint).

Performance monitoring:
    - Every phase timed (import, quantize, load, inference, save)
    - Per-step diffusion callback shows progress during inference
    - GPU temp/power/clock tracked via nvidia-smi
    - Persistent log at /tmp/local-models-gen/logs/performance.log
    - `local_perf_report` tool for querying from Claude Code

Usage:
    python3.11 scripts/mcp/local_models_mcp.py          # stdio (Claude Code)
    python3.11 scripts/mcp/local_models_mcp.py --http    # HTTP server (debug)
"""

from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import time
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import torch
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator, ConfigDict

# =============================================================================
# Constants
# =============================================================================

OUTPUT_DIR = Path("/tmp/local-models-gen")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = Path("/tmp/local-models-gen/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "performance.log"

IDLE_UNLOAD_SECONDS = 1800  # Unload model after 30 minutes idle (was 5 min)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Pre-quantized model cache — avoids 10-min NF4 quantization on every cold start
NF4_CACHE_DIR = Path.home() / ".cache" / "local-models-mcp" / "z-image-nf4"

# Z-Image Turbo: guidance_scale MUST be 0.0 (CFG baked into distilled model)
Z_IMAGE_GUIDANCE_SCALE = 0.0

# Z-Image Turbo: 9 inference steps (8 DiT forward passes + 1 final)
Z_IMAGE_INFERENCE_STEPS = 9

# Original model ID for non-quantized components (VAE, tokenizer, scheduler)
Z_IMAGE_MODEL_ID = "Tongyi-MAI/Z-Image-Turbo"

_server_start_time = time.time()


# =============================================================================
# Logging — stderr + persistent file + GPU telemetry
# =============================================================================


def _log(msg: str, *, level: str = "INFO") -> None:
    """Log to stderr AND persistent file. Timestamps on both."""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[local-models-mcp] [{ts}] {msg}", file=sys.stderr, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{datetime.now().isoformat()} | {level:5s} | {msg}\n")
    except OSError:
        pass


def _gpu_telemetry() -> dict:
    """Read GPU temp, power, clock, fan from nvidia-smi. Non-blocking."""
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu,power.draw,clocks.current.sm,fan.speed,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=2,
        )
        if out.returncode == 0:
            parts = [p.strip() for p in out.stdout.strip().split(",")]
            return {
                "temp_c": int(parts[0]) if parts[0] != "[N/A]" else None,
                "power_w": float(parts[1]) if parts[1] != "[N/A]" else None,
                "clock_mhz": int(parts[2]) if parts[2] != "[N/A]" else None,
                "fan_pct": int(parts[3]) if parts[3] != "[N/A]" else None,
                "util_pct": int(parts[4]) if parts[4] != "[N/A]" else None,
            }
    except Exception:
        pass
    return {}


def _vram_snapshot() -> str:
    """Quick VRAM snapshot string."""
    if not torch.cuda.is_available():
        return "VRAM: N/A"
    alloc = torch.cuda.memory_allocated(0) / 1e9
    reserved = torch.cuda.memory_reserved(0) / 1e9
    total = torch.cuda.get_device_properties(0).total_memory / 1e9
    return f"VRAM: {alloc:.2f}GB alloc / {reserved:.2f}GB rsv / {total:.2f}GB total"


def _vram_dict() -> dict:
    """VRAM as dict for JSON responses."""
    if not torch.cuda.is_available():
        return {"available": False}
    props = torch.cuda.get_device_properties(0)
    return {
        "device": torch.cuda.get_device_name(0),
        "total_gb": round(props.total_memory / 1e9, 2),
        "allocated_gb": round(torch.cuda.memory_allocated(0) / 1e9, 2),
        "reserved_gb": round(torch.cuda.memory_reserved(0) / 1e9, 2),
        "free_gb": round((props.total_memory - torch.cuda.memory_reserved(0)) / 1e9, 2),
    }


class _BackgroundMonitor:
    """Background thread that logs VRAM + GPU telemetry every N seconds during long operations."""

    def __init__(self, interval: float = 5.0, label: str = ""):
        self._interval = interval
        self._label = label
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        tick = 0
        while not self._stop.wait(self._interval):
            tick += 1
            elapsed = tick * self._interval
            gpu = _gpu_telemetry()
            vram_alloc = torch.cuda.memory_allocated(0) / 1e9 if torch.cuda.is_available() else 0
            vram_rsv = torch.cuda.memory_reserved(0) / 1e9 if torch.cuda.is_available() else 0
            gpu_str = ""
            if gpu:
                gpu_str = f" | GPU: {gpu.get('temp_c', '?')}C {gpu.get('power_w', '?')}W util={gpu.get('util_pct', '?')}%"
            _log(f"   ... [{self._label}] {elapsed:.0f}s elapsed | VRAM: {vram_alloc:.2f}GB alloc / {vram_rsv:.2f}GB rsv{gpu_str}")


@contextmanager
def _perf_phase(name: str, monitor_interval: float = 0):
    """Context manager — logs timing + VRAM delta + GPU telemetry per phase.

    If monitor_interval > 0, spawns a background thread that logs VRAM/GPU
    every N seconds while the phase is running (for long-running phases like model loading).
    """
    gpu = _gpu_telemetry()
    gpu_str = f" | GPU: {gpu.get('temp_c', '?')}C {gpu.get('power_w', '?')}W {gpu.get('util_pct', '?')}%" if gpu else ""
    _log(f">> START {name} ({_vram_snapshot()}{gpu_str})")
    monitor = None
    if monitor_interval > 0:
        monitor = _BackgroundMonitor(interval=monitor_interval, label=name.split(":")[0].strip() if ":" in name else name)
        monitor.start()
    t0 = time.time()
    vram_before = torch.cuda.memory_allocated(0) / 1e9 if torch.cuda.is_available() else 0
    yield
    if monitor:
        monitor.stop()
    elapsed = time.time() - t0
    vram_after = torch.cuda.memory_allocated(0) / 1e9 if torch.cuda.is_available() else 0
    delta = vram_after - vram_before
    sign = "+" if delta >= 0 else ""
    gpu2 = _gpu_telemetry()
    gpu_str2 = f" | GPU: {gpu2.get('temp_c', '?')}C {gpu2.get('power_w', '?')}W" if gpu2 else ""
    _log(f"<< DONE  {name} — {elapsed:.2f}s (VRAM {sign}{delta:.2f}GB -> {vram_after:.2f}GB{gpu_str2})")


# =============================================================================
# Model Manager
# =============================================================================


class ModelManager:
    """Manages GPU model lifecycle: load on demand, unload on idle."""

    def __init__(self) -> None:
        self._pipelines: dict[str, object] = {}
        self._last_used: dict[str, float] = {}
        self._lock = threading.Lock()
        self._unload_timer: Optional[threading.Timer] = None
        self._load_history: list[dict] = []
        self._gen_history: list[dict] = []

    def _schedule_unload(self) -> None:
        if self._unload_timer:
            self._unload_timer.cancel()
        self._unload_timer = threading.Timer(IDLE_UNLOAD_SECONDS, self._check_idle)
        self._unload_timer.daemon = True
        self._unload_timer.start()

    def _check_idle(self) -> None:
        now = time.time()
        with self._lock:
            stale = [k for k, t in self._last_used.items() if now - t > IDLE_UNLOAD_SECONDS]
            for key in stale:
                self._unload(key)

    def _unload(self, key: str) -> None:
        if key in self._pipelines:
            del self._pipelines[key]
            del self._last_used[key]
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            _log(f"Unloaded '{key}' — {_vram_snapshot()}")

    def unload_all(self) -> None:
        with self._lock:
            for key in list(self._pipelines.keys()):
                self._unload(key)

    def _has_nf4_cache(self) -> bool:
        """Check if pre-quantized NF4 cache exists."""
        marker = NF4_CACHE_DIR / "transformer" / "config.json"
        return marker.exists()

    def _load_from_cache(self) -> object:
        """FAST PATH: Load pre-quantized components from disk cache (~30-60s)."""
        from diffusers import ZImagePipeline, AutoModel

        phase_timings: dict[str, float] = {}

        _log("=" * 60)
        _log("Z-IMAGE TURBO — LOADING FROM NF4 CACHE (FAST PATH)")
        _log(f"Cache: {NF4_CACHE_DIR}")

        # Load pre-quantized transformer
        t0 = time.time()
        with _perf_phase("Cache 1/3: Load NF4 transformer", monitor_interval=5):
            transformer = AutoModel.from_pretrained(
                str(NF4_CACHE_DIR / "transformer"),
                torch_dtype=torch.bfloat16,
            )
        phase_timings["load_transformer"] = round(time.time() - t0, 2)

        # Load pre-quantized text_encoder
        t0 = time.time()
        with _perf_phase("Cache 2/3: Load NF4 text_encoder", monitor_interval=5):
            from transformers import AutoModel as TFAutoModel
            text_encoder = TFAutoModel.from_pretrained(
                str(NF4_CACHE_DIR / "text_encoder"),
                torch_dtype=torch.bfloat16,
            )
        phase_timings["load_text_encoder"] = round(time.time() - t0, 2)

        # Assemble pipeline with cached quantized components + original non-quantized parts
        t0 = time.time()
        with _perf_phase("Cache 3/3: Assemble pipeline + move to GPU", monitor_interval=5):
            pipe = ZImagePipeline.from_pretrained(
                Z_IMAGE_MODEL_ID,
                transformer=transformer,
                text_encoder=text_encoder,
                torch_dtype=torch.bfloat16,
            )
            pipe.to(DEVICE)
        phase_timings["assemble"] = round(time.time() - t0, 2)

        return pipe, phase_timings

    def _load_and_quantize(self) -> object:
        """SLOW PATH: Quantize from scratch (~10 min), then save to cache."""
        from diffusers import ZImagePipeline
        from diffusers.quantizers import PipelineQuantizationConfig

        phase_timings: dict[str, float] = {}

        _log("=" * 60)
        _log("Z-IMAGE TURBO NF4 — QUANTIZING FROM SCRATCH (SLOW PATH)")
        _log("This takes ~10 min. Next time will use cache (~30-60s).")

        # Config
        t0 = time.time()
        with _perf_phase("Quantize 1/4: Build NF4 config"):
            quant_config = PipelineQuantizationConfig(
                quant_backend="bitsandbytes_4bit",
                quant_kwargs={
                    "load_in_4bit": True,
                    "bnb_4bit_quant_type": "nf4",
                    "bnb_4bit_compute_dtype": torch.bfloat16,
                    "bnb_4bit_use_double_quant": True,
                },
                components_to_quantize=["transformer", "text_encoder"],
            )
        phase_timings["config"] = round(time.time() - t0, 2)

        # from_pretrained (THE BIG ONE — reads 31GB, quantizes to NF4)
        t0 = time.time()
        with _perf_phase("Quantize 2/4: from_pretrained + NF4 quantize (31GB -> ~5GB)", monitor_interval=5):
            pipe = ZImagePipeline.from_pretrained(
                Z_IMAGE_MODEL_ID,
                quantization_config=quant_config,
                torch_dtype=torch.bfloat16,
            )
        phase_timings["from_pretrained"] = round(time.time() - t0, 2)

        # Save quantized components to cache
        t0 = time.time()
        with _perf_phase("Quantize 3/4: Save NF4 cache to disk", monitor_interval=5):
            NF4_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            pipe.transformer.save_pretrained(str(NF4_CACHE_DIR / "transformer"))
            pipe.text_encoder.save_pretrained(str(NF4_CACHE_DIR / "text_encoder"))
            # Write a marker with metadata
            marker = {
                "model_id": Z_IMAGE_MODEL_ID,
                "quant_type": "nf4",
                "double_quant": True,
                "components": ["transformer", "text_encoder"],
                "created": datetime.now().isoformat(),
            }
            (NF4_CACHE_DIR / "cache_info.json").write_text(json.dumps(marker, indent=2))
        phase_timings["save_cache"] = round(time.time() - t0, 2)
        _log(f"NF4 cache saved to {NF4_CACHE_DIR}")

        # Move to GPU
        t0 = time.time()
        with _perf_phase("Quantize 4/4: Move to GPU", monitor_interval=5):
            pipe.to(DEVICE)
        phase_timings["to_device"] = round(time.time() - t0, 2)

        return pipe, phase_timings

    def get_z_image(self) -> object:
        """Load Z-Image Turbo. Uses NF4 cache if available (fast), else quantizes from scratch (slow, once)."""
        with self._lock:
            if "z_image" not in self._pipelines:
                load_start = time.time()

                _log(f"{_vram_snapshot()}")
                gpu = _gpu_telemetry()
                if gpu:
                    _log(f"GPU: {gpu.get('temp_c')}C | {gpu.get('power_w')}W | {gpu.get('clock_mhz')}MHz | fan {gpu.get('fan_pct')}% | util {gpu.get('util_pct')}%")

                # Unload any other models first
                for key in list(self._pipelines.keys()):
                    self._unload(key)

                # Import diffusers (needed for both paths)
                t0 = time.time()
                with _perf_phase("Phase 0: Import diffusers", monitor_interval=10):
                    import diffusers  # noqa: F401 — ensures module is loaded
                import_time = round(time.time() - t0, 2)

                # Choose fast or slow path
                if self._has_nf4_cache():
                    pipe, phase_timings = self._load_from_cache()
                    phase_timings["import"] = import_time
                    load_type = "CACHE"
                else:
                    pipe, phase_timings = self._load_and_quantize()
                    phase_timings["import"] = import_time
                    load_type = "QUANTIZE"

                self._pipelines["z_image"] = pipe

                total = time.time() - load_start
                _log(f"TOTAL LOAD ({load_type}): {total:.1f}s")
                _log(f"  phases: {json.dumps(phase_timings)}")
                _log(f"{_vram_snapshot()}")
                _log("=" * 60)

                self._load_history.append({
                    "model": "z_image",
                    "load_type": load_type,
                    "timestamp": datetime.now().isoformat(),
                    "total_seconds": round(total, 2),
                    "phase_timings": phase_timings,
                    "vram_gb": round(torch.cuda.memory_allocated(0) / 1e9, 2) if torch.cuda.is_available() else 0,
                    "gpu": _gpu_telemetry(),
                })

            self._last_used["z_image"] = time.time()
            self._schedule_unload()
            return self._pipelines["z_image"]


    def get_hunyuan3d(self) -> object:
        """Load Hunyuan3D 2 Mini for image-to-3D mesh generation. ~6GB VRAM."""
        with self._lock:
            if "hunyuan3d" not in self._pipelines:
                load_start = time.time()

                _log(f"{_vram_snapshot()}")
                gpu = _gpu_telemetry()
                if gpu:
                    _log(f"GPU: {gpu.get('temp_c')}C | {gpu.get('power_w')}W | util {gpu.get('util_pct')}%")

                # Unload any other models first
                for key in list(self._pipelines.keys()):
                    self._unload(key)

                phase_timings: dict[str, float] = {}

                _log("=" * 60)
                _log("HUNYUAN3D 2 MINI — LOADING (image-to-3D, 0.6B params)")

                t0 = time.time()
                with _perf_phase("Hunyuan3D 1/2: Import hy3dgen", monitor_interval=5):
                    from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
                phase_timings["import"] = round(time.time() - t0, 2)

                t0 = time.time()
                with _perf_phase("Hunyuan3D 2/2: from_pretrained + move to GPU", monitor_interval=5):
                    pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                        "tencent/Hunyuan3D-2mini",
                        subfolder="hunyuan3d-dit-v2-mini",
                        variant="fp16",
                        use_safetensors=True,
                        device=DEVICE,
                        dtype=torch.float16,
                    )
                phase_timings["load"] = round(time.time() - t0, 2)

                self._pipelines["hunyuan3d"] = pipe

                total = time.time() - load_start
                _log(f"TOTAL LOAD: {total:.1f}s")
                _log(f"  phases: {json.dumps(phase_timings)}")
                _log(f"{_vram_snapshot()}")
                _log("=" * 60)

                self._load_history.append({
                    "model": "hunyuan3d",
                    "load_type": "STANDARD",
                    "timestamp": datetime.now().isoformat(),
                    "total_seconds": round(total, 2),
                    "phase_timings": phase_timings,
                    "vram_gb": round(torch.cuda.memory_allocated(0) / 1e9, 2) if torch.cuda.is_available() else 0,
                    "gpu": _gpu_telemetry(),
                })

            self._last_used["hunyuan3d"] = time.time()
            self._schedule_unload()
            return self._pipelines["hunyuan3d"]


_manager = ModelManager()


# =============================================================================
# Diffusion step callback — per-step progress logging
# =============================================================================


def _make_step_callback(total_steps: int):
    """Create a callback that logs each diffusion step with timing."""
    state = {"step_start": time.time(), "gen_start": time.time()}

    def callback(pipe, step_index, timestep, callback_kwargs):
        now = time.time()
        step_time = now - state["step_start"]
        elapsed = now - state["gen_start"]
        remaining = (elapsed / max(step_index + 1, 1)) * (total_steps - step_index - 1)
        _log(
            f"  Step {step_index + 1}/{total_steps} — "
            f"{step_time:.2f}s/step | elapsed {elapsed:.1f}s | ETA {remaining:.1f}s"
        )
        state["step_start"] = now
        return callback_kwargs

    return callback


# =============================================================================
# FastMCP Server + Tools
# =============================================================================

mcp = FastMCP("local_models_mcp")


class GenerateImageInput(BaseModel):
    """Input for Z-Image Turbo text-to-image generation."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    prompt: str = Field(
        ...,
        description="Text prompt for image. Be descriptive — style, lighting, composition.",
        min_length=1, max_length=2000,
    )
    width: int = Field(default=1024, description="Width in px (divisible by 8, 256-2048).", ge=256, le=2048)
    height: int = Field(default=1024, description="Height in px (divisible by 8, 256-2048).", ge=256, le=2048)
    seed: int = Field(default=-1, description="Random seed (-1 = random).", ge=-1)
    output_path: Optional[str] = Field(default=None, description="Custom output path (PNG). Auto if omitted.")

    @field_validator("width", "height")
    @classmethod
    def must_be_divisible_by_8(cls, v: int) -> int:
        if v % 8 != 0:
            raise ValueError(f"Must be divisible by 8, got {v}. Try {v - (v % 8)}.")
        return v


class UnloadModelsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: bool = Field(default=True, description="Confirm unload.")


@mcp.tool(
    name="local_generate_image",
    annotations={"title": "Generate Image (Z-Image Turbo NF4, Local GPU)", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
)
async def local_generate_image(params: GenerateImageInput) -> str:
    """Generate an image from text using Z-Image Turbo on local GPU (FREE).

    Returns JSON with path, timings breakdown, VRAM usage, and GPU telemetry.
    First call loads model (~2-5 min). Subsequent calls ~5-15s.
    """
    total_start = time.time()
    timings: dict[str, float] = {}

    try:
        _log("=" * 50)
        _log(f"GENERATE: {params.width}x{params.height} seed={params.seed}")
        _log(f"Prompt: {params.prompt[:100]}{'...' if len(params.prompt) > 100 else ''}")
        gpu_before = _gpu_telemetry()

        # Model load (cached after first call)
        t0 = time.time()
        pipe = _manager.get_z_image()
        timings["model_load"] = round(time.time() - t0, 2)
        cached = timings["model_load"] < 1.0
        _log(f"Model: {timings['model_load']}s {'(cached)' if cached else '(COLD START)'}")

        # Seed
        actual_seed = params.seed if params.seed >= 0 else int(time.time() * 1000) % (2**32)
        generator = torch.Generator(DEVICE).manual_seed(actual_seed)

        # Inference with per-step callback
        t0 = time.time()
        step_cb = _make_step_callback(Z_IMAGE_INFERENCE_STEPS)
        _log(f"Inference: {Z_IMAGE_INFERENCE_STEPS} steps, guidance={Z_IMAGE_GUIDANCE_SCALE}")
        result = pipe(
            prompt=params.prompt,
            num_inference_steps=Z_IMAGE_INFERENCE_STEPS,
            guidance_scale=Z_IMAGE_GUIDANCE_SCALE,
            width=params.width,
            height=params.height,
            generator=generator,
            callback_on_step_end=step_cb,
        )
        image = result.images[0]
        timings["inference"] = round(time.time() - t0, 2)
        _log(f"Inference: {timings['inference']}s ({timings['inference'] / Z_IMAGE_INFERENCE_STEPS:.2f}s/step avg)")

        # Save
        t0 = time.time()
        if params.output_path:
            out_path = Path(params.output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            out_path = OUTPUT_DIR / f"zimg_{int(time.time())}_{actual_seed}.png"
        image.save(str(out_path), "PNG")
        file_size_mb = out_path.stat().st_size / 1e6
        timings["save"] = round(time.time() - t0, 2)

        total_elapsed = round(time.time() - total_start, 2)
        timings["total"] = total_elapsed
        gpu_after = _gpu_telemetry()
        vram = _vram_dict()

        _log(f"DONE: {out_path.name} ({file_size_mb:.1f}MB) in {total_elapsed}s")
        _log(f"  load={timings['model_load']}s | inference={timings['inference']}s | save={timings['save']}s")
        if gpu_after:
            _log(f"  GPU: {gpu_after.get('temp_c')}C | {gpu_after.get('power_w')}W | util {gpu_after.get('util_pct')}%")
        _log("=" * 50)

        # History
        gen_record = {
            "timestamp": datetime.now().isoformat(),
            "resolution": f"{params.width}x{params.height}",
            "seed": actual_seed,
            "file_size_mb": round(file_size_mb, 2),
            "timings": timings,
            "gpu_before": gpu_before,
            "gpu_after": gpu_after,
            "vram": vram,
        }
        _manager._gen_history.append(gen_record)

        return json.dumps({
            "status": "success",
            "path": str(out_path),
            "model": "Z-Image Turbo NF4 (6B, Apache 2.0)",
            "resolution": f"{params.width}x{params.height}",
            "seed": actual_seed,
            "file_size_mb": round(file_size_mb, 2),
            "timings": timings,
            "time_seconds": total_elapsed,
            "gpu": gpu_after,
            "vram": vram,
            "cost": "$0.00",
        }, indent=2)

    except torch.cuda.OutOfMemoryError:
        _log("OOM! Unloading all models.", level="ERROR")
        _manager.unload_all()
        return json.dumps({
            "status": "error",
            "error": "VRAM out of memory",
            "message": f"Not enough VRAM for {params.width}x{params.height}. Try 768x768 or unload Ollama.",
            "vram": _vram_dict(),
            "gpu": _gpu_telemetry(),
        }, indent=2)

    except Exception as exc:
        _log(f"ERROR: {type(exc).__name__}: {exc}", level="ERROR")
        return json.dumps({
            "status": "error",
            "error": type(exc).__name__,
            "message": str(exc),
            "vram": _vram_dict(),
            "gpu": _gpu_telemetry(),
        }, indent=2)


@mcp.tool(
    name="local_vram_status",
    annotations={"title": "GPU VRAM + Telemetry", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def local_vram_status() -> str:
    """Check GPU VRAM usage, loaded models, temperature, power, utilization."""
    return json.dumps({
        "vram": _vram_dict(),
        "gpu": _gpu_telemetry(),
        "loaded_models": list(_manager._pipelines.keys()),
        "server_uptime_seconds": round(time.time() - _server_start_time, 1),
    }, indent=2)


@mcp.tool(
    name="local_unload_models",
    annotations={"title": "Unload All Models (Free VRAM)", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def local_unload_models(params: UnloadModelsInput) -> str:
    """Unload all loaded models and free GPU VRAM."""
    if not params.confirm:
        return json.dumps({"status": "cancelled"})

    before = _vram_dict()
    _manager.unload_all()
    after = _vram_dict()
    return json.dumps({"status": "success", "before": before, "after": after}, indent=2)


@mcp.tool(
    name="local_save_cache",
    annotations={"title": "Save NF4 Cache (one-time)", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def local_save_cache() -> str:
    """Save currently loaded Z-Image model's quantized components to disk cache.

    After this, cold starts drop from ~10 min to ~30-60s.
    Model must be loaded first (call local_generate_image or wait for it to load).
    """
    if "z_image" not in _manager._pipelines:
        return json.dumps({
            "status": "error",
            "error": "No model loaded",
            "message": "Generate an image first to load the model, then call this to save the cache.",
        })

    pipe = _manager._pipelines["z_image"]

    if _manager._has_nf4_cache():
        cache_size = sum(f.stat().st_size for f in NF4_CACHE_DIR.rglob("*") if f.is_file())
        return json.dumps({
            "status": "already_cached",
            "cache_dir": str(NF4_CACHE_DIR),
            "cache_size_gb": round(cache_size / 1e9, 2),
            "message": "Cache already exists. Delete it to re-create.",
        })

    t0 = time.time()
    with _perf_phase("Save NF4 cache: transformer + text_encoder", monitor_interval=5):
        NF4_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        pipe.transformer.save_pretrained(str(NF4_CACHE_DIR / "transformer"))
        pipe.text_encoder.save_pretrained(str(NF4_CACHE_DIR / "text_encoder"))
        marker = {
            "model_id": Z_IMAGE_MODEL_ID,
            "quant_type": "nf4",
            "double_quant": True,
            "components": ["transformer", "text_encoder"],
            "created": datetime.now().isoformat(),
        }
        (NF4_CACHE_DIR / "cache_info.json").write_text(json.dumps(marker, indent=2))

    elapsed = round(time.time() - t0, 2)
    cache_size = sum(f.stat().st_size for f in NF4_CACHE_DIR.rglob("*") if f.is_file())
    _log(f"NF4 cache saved: {cache_size / 1e9:.2f}GB in {elapsed}s")

    return json.dumps({
        "status": "success",
        "cache_dir": str(NF4_CACHE_DIR),
        "cache_size_gb": round(cache_size / 1e9, 2),
        "save_time_seconds": elapsed,
        "message": "Cache saved! Next cold start will use fast path (~30-60s instead of ~10min).",
    }, indent=2)


class Generate3DInput(BaseModel):
    """Input for Hunyuan3D 2 Mini image-to-3D mesh generation."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    image_path: str = Field(
        ...,
        description="Path to input image (PNG/JPG). Use local_generate_image first to create from text.",
        min_length=1,
    )
    num_inference_steps: int = Field(
        default=50,
        description="Diffusion steps (more = better quality, slower). 30-50 recommended.",
        ge=10, le=100,
    )
    octree_resolution: int = Field(
        default=256,
        description="Mesh resolution. 256 = fast/lower detail, 384 = high detail, 512 = max detail.",
        ge=128, le=512,
    )
    seed: int = Field(default=-1, description="Random seed (-1 = random).", ge=-1)
    output_path: Optional[str] = Field(default=None, description="Custom output path (.glb). Auto if omitted.")
    remove_background: bool = Field(default=True, description="Auto-remove image background before processing.")


@mcp.tool(
    name="local_generate_3d",
    annotations={"title": "Generate 3D Mesh (Hunyuan3D 2 Mini, Local GPU)", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
)
async def local_generate_3d(params: Generate3DInput) -> str:
    """Generate a 3D mesh (.glb) from an image using Hunyuan3D 2 Mini on local GPU (FREE).

    Workflow: Use local_generate_image first to create an image from text, then pass that image here.
    Returns JSON with path to .glb file, timings, VRAM usage, and GPU telemetry.
    First call downloads model (~2GB). Subsequent calls faster.
    """
    total_start = time.time()
    timings: dict[str, float] = {}

    try:
        _log("=" * 50)
        _log(f"GENERATE 3D: steps={params.num_inference_steps} octree={params.octree_resolution}")
        _log(f"Image: {params.image_path}")
        gpu_before = _gpu_telemetry()

        # Validate input image
        img_path = Path(params.image_path)
        if not img_path.exists():
            return json.dumps({
                "status": "error",
                "error": "File not found",
                "message": f"Image not found: {params.image_path}. Generate one with local_generate_image first.",
            })

        # Optionally remove background
        if params.remove_background:
            t0 = time.time()
            with _perf_phase("3D: Remove background (rembg)"):
                from rembg import remove
                from PIL import Image
                img = Image.open(str(img_path))
                img = remove(img)
                # Save to temp for pipeline input
                rembg_path = OUTPUT_DIR / f"rembg_{int(time.time())}.png"
                img.save(str(rembg_path))
                input_image = str(rembg_path)
            timings["rembg"] = round(time.time() - t0, 2)
            _log(f"Background removed: {timings['rembg']}s")
        else:
            input_image = str(img_path)

        # Model load
        t0 = time.time()
        pipe = _manager.get_hunyuan3d()
        timings["model_load"] = round(time.time() - t0, 2)
        cached = timings["model_load"] < 1.0
        _log(f"Model: {timings['model_load']}s {'(cached)' if cached else '(COLD START)'}")

        # Seed
        actual_seed = params.seed if params.seed >= 0 else int(time.time() * 1000) % (2**32)
        generator = torch.Generator(DEVICE).manual_seed(actual_seed)

        # Inference
        t0 = time.time()
        _log(f"Inference: {params.num_inference_steps} steps, octree={params.octree_resolution}")
        mesh = pipe(
            image=input_image,
            num_inference_steps=params.num_inference_steps,
            guidance_scale=5.0,
            generator=generator,
            octree_resolution=params.octree_resolution,
            output_type="trimesh",
        )[0]
        timings["inference"] = round(time.time() - t0, 2)
        _log(f"Inference: {timings['inference']}s")

        # Save mesh
        t0 = time.time()
        if params.output_path:
            out_path = Path(params.output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            out_path = OUTPUT_DIR / f"mesh_{int(time.time())}_{actual_seed}.glb"

        mesh.export(str(out_path))
        file_size_mb = out_path.stat().st_size / 1e6
        timings["save"] = round(time.time() - t0, 2)

        # Mesh stats
        mesh_stats = {
            "vertices": len(mesh.vertices) if hasattr(mesh, 'vertices') else "unknown",
            "faces": len(mesh.faces) if hasattr(mesh, 'faces') else "unknown",
        }

        total_elapsed = round(time.time() - total_start, 2)
        timings["total"] = total_elapsed
        gpu_after = _gpu_telemetry()
        vram = _vram_dict()

        _log(f"DONE: {out_path.name} ({file_size_mb:.1f}MB) in {total_elapsed}s")
        _log(f"  load={timings['model_load']}s | inference={timings['inference']}s | save={timings['save']}s")
        _log(f"  Mesh: {mesh_stats['vertices']} verts, {mesh_stats['faces']} faces")
        if gpu_after:
            _log(f"  GPU: {gpu_after.get('temp_c')}C | {gpu_after.get('power_w')}W | util {gpu_after.get('util_pct')}%")
        _log("=" * 50)

        # History
        gen_record = {
            "timestamp": datetime.now().isoformat(),
            "type": "3d_mesh",
            "seed": actual_seed,
            "file_size_mb": round(file_size_mb, 2),
            "mesh_stats": mesh_stats,
            "timings": timings,
            "gpu_before": gpu_before,
            "gpu_after": gpu_after,
            "vram": vram,
        }
        _manager._gen_history.append(gen_record)

        return json.dumps({
            "status": "success",
            "path": str(out_path),
            "model": "Hunyuan3D 2 Mini (0.6B, Apache 2.0)",
            "mesh": mesh_stats,
            "file_size_mb": round(file_size_mb, 2),
            "timings": timings,
            "time_seconds": total_elapsed,
            "gpu": gpu_after,
            "vram": vram,
            "cost": "$0.00",
            "tip": "Open .glb in https://gltf-viewer.donmccurdy.com/ or Three.js",
        }, indent=2)

    except torch.cuda.OutOfMemoryError:
        _log("OOM! Unloading all models.", level="ERROR")
        _manager.unload_all()
        return json.dumps({
            "status": "error",
            "error": "VRAM out of memory",
            "message": "Not enough VRAM for 3D generation. Try lower octree_resolution (256) or unload Ollama.",
            "vram": _vram_dict(),
            "gpu": _gpu_telemetry(),
        }, indent=2)

    except Exception as exc:
        _log(f"ERROR: {type(exc).__name__}: {exc}", level="ERROR")
        import traceback
        _log(traceback.format_exc(), level="ERROR")
        return json.dumps({
            "status": "error",
            "error": type(exc).__name__,
            "message": str(exc),
            "vram": _vram_dict(),
            "gpu": _gpu_telemetry(),
        }, indent=2)


@mcp.tool(
    name="local_perf_report",
    annotations={"title": "Performance Report", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def local_perf_report() -> str:
    """Full performance report: load history, generation history, averages, GPU telemetry, recent logs.

    Call this to diagnose slowness. Shows every phase breakdown.
    """
    # Compute stats
    gens = _manager._gen_history
    avg_inference = round(sum(g["timings"]["inference"] for g in gens) / len(gens), 2) if gens else None
    avg_total = round(sum(g["timings"]["total"] for g in gens) / len(gens), 2) if gens else None
    min_inference = round(min(g["timings"]["inference"] for g in gens), 2) if gens else None
    max_inference = round(max(g["timings"]["inference"] for g in gens), 2) if gens else None

    # Recent log lines
    recent_logs: list[str] = []
    try:
        with open(LOG_FILE) as f:
            recent_logs = [l.strip() for l in f.readlines()[-80:]]
    except OSError:
        recent_logs = ["(no log file)"]

    return json.dumps({
        "server_uptime_seconds": round(time.time() - _server_start_time, 1),
        "vram": _vram_dict(),
        "gpu": _gpu_telemetry(),
        "loaded_models": list(_manager._pipelines.keys()),
        "model_loads": _manager._load_history,
        "generation_stats": {
            "count": len(gens),
            "avg_inference_s": avg_inference,
            "min_inference_s": min_inference,
            "max_inference_s": max_inference,
            "avg_total_s": avg_total,
        },
        "generation_history": gens[-10:],
        "log_file": str(LOG_FILE),
        "recent_logs": recent_logs,
    }, indent=2)


# =============================================================================
# Vision Review Tools — Qwen3-VL (local) + Gemini (cloud)
# =============================================================================

class VisionReviewInput(BaseModel):
    """Input for vision review tools."""
    model_config = ConfigDict(extra="forbid")
    image_path: str = Field(description="Path to the image file to review")
    prompt: str = Field(
        default="Rate this UI design 1-10. Is the layout balanced? Colors harmonious? What would improve it?",
        description="What to ask the vision model about the image"
    )


@mcp.tool(
    name="local_vision_review",
    annotations={"title": "Qwen3-VL Vision Review (FREE, local GPU)", "readOnlyHint": True},
)
async def local_vision_review(params: VisionReviewInput) -> str:
    """Review an image using Qwen3-VL via local Ollama. FREE, runs on GPU.

    Use for: UI screenshots, landing page checks, generated assets, layout review.
    Qwen3-VL reads Korean text, identifies UI elements, critiques color/composition.

    Example: local_vision_review(image_path="/tmp/screenshot.png", prompt="Is this hero section premium? Rate 1-10.")
    """
    import base64
    import urllib.request

    image_path = Path(params.image_path)
    if not image_path.exists():
        return json.dumps({"error": f"Image not found: {params.image_path}"})

    # Convert to WebP if PNG/JPG for faster processing
    review_path = image_path
    if image_path.suffix.lower() in ('.png', '.jpg', '.jpeg'):
        webp_path = Path(f"/tmp/qwen-review/{image_path.stem}.webp")
        webp_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(["cwebp", "-q", "80", str(image_path), "-o", str(webp_path)],
                          capture_output=True, timeout=30)
            if webp_path.exists():
                review_path = webp_path
        except Exception:
            pass  # Use original if cwebp fails

    with open(review_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    payload = json.dumps({
        "model": "qwen3-vl:8b",
        "messages": [
            {"role": "system", "content": "Concise UI reviewer. Under 80 words. Direct answer."},
            {"role": "user", "content": params.prompt, "images": [img_b64]}
        ],
        "stream": False,
        "options": {"num_predict": 1500}
    }).encode()

    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=300)
        raw = json.loads(resp.read())["message"]["content"]
        # Strip thinking tags
        if "</think>" in raw:
            raw = raw.split("</think>")[-1].strip()
        return json.dumps({"model": "qwen3-vl:8b", "review": raw, "image": str(image_path), "cost": "FREE"})
    except Exception as exc:
        return json.dumps({"error": str(exc), "model": "qwen3-vl:8b"})


class GeminiVisionInput(BaseModel):
    """Input for Gemini vision review."""
    model_config = ConfigDict(extra="forbid")
    image_path: str = Field(description="Path to the image file to review")
    prompt: str = Field(
        default="You are a senior UI/UX designer. Review this page design. Rate 1-10 for premium feel. Analyze: color harmony, visual hierarchy, typography, spacing, balance. Suggest specific improvements. Be detailed but concise.",
        description="What to ask Gemini about the image"
    )


@mcp.tool(
    name="gemini_vision_review",
    annotations={"title": "Gemini 3 Pro Vision Review (PAID, cloud)", "readOnlyHint": True},
)
async def gemini_vision_review(params: GeminiVisionInput) -> str:
    """Deep design critique using Google Gemini 3 Pro vision. PAID (Google API).

    More powerful than Qwen3-VL — hundreds of billions of parameters.
    Use for milestone reviews, deep design critique, final quality checks.
    Use local_vision_review (Qwen3-VL) for quick free checks during development.

    Requires: GEMINI_API_KEY in /home/neil1988/.nano-banana/.env
    """
    image_path = Path(params.image_path)
    if not image_path.exists():
        return json.dumps({"error": f"Image not found: {params.image_path}"})

    # Load API key
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        env_file = Path.home() / ".nano-banana" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key:
        return json.dumps({"error": "GEMINI_API_KEY not found. Set in ~/.nano-banana/.env"})

    try:
        from google import genai
        from google.genai import types
        from PIL import Image

        client = genai.Client(api_key=api_key)
        img = Image.open(image_path)

        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[params.prompt, img],
            config=types.GenerateContentConfig(response_modalities=["TEXT"]),
        )

        review_text = response.text if response.text else "No response from Gemini"
        return json.dumps({"model": "gemini-3-pro", "review": review_text, "image": str(image_path), "cost": "PAID"})
    except Exception as exc:
        return json.dumps({"error": str(exc), "model": "gemini-3-pro"})


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    if "--prequantize" in sys.argv:
        # Standalone mode: quantize and save to cache, then exit
        _log("=" * 60)
        _log("PRE-QUANTIZE MODE — One-time NF4 cache creation")
        _log(f"Device: {DEVICE}")
        _log(f"{_vram_snapshot()}")
        _log(f"Cache dir: {NF4_CACHE_DIR}")

        if _manager._has_nf4_cache():
            _log("NF4 cache already exists! To re-quantize, delete it first:")
            _log(f"  rm -rf {NF4_CACHE_DIR}")
            _log("=" * 60)
            sys.exit(0)

        _log("Starting quantization (this takes ~10 min, one time only)...")
        _log("=" * 60)

        # Import first
        t0 = time.time()
        with _perf_phase("Import diffusers", monitor_interval=10):
            import diffusers  # noqa: F401
        _log(f"Import: {time.time() - t0:.1f}s")

        # Quantize and save
        pipe, timings = _manager._load_and_quantize()
        _log(f"Pre-quantization complete! Timings: {json.dumps(timings)}")
        _log(f"Cache saved to: {NF4_CACHE_DIR}")

        # Show cache size
        cache_size = sum(f.stat().st_size for f in NF4_CACHE_DIR.rglob("*") if f.is_file())
        _log(f"Cache size: {cache_size / 1e9:.2f}GB")
        _log("Next server start will use fast cache path (~30-60s instead of ~10min)")
        _log("=" * 60)
        sys.exit(0)

    _log("=" * 60)
    _log(f"LOCAL MODELS MCP SERVER STARTING")
    _log(f"Device: {DEVICE}")
    _log(f"{_vram_snapshot()}")
    gpu = _gpu_telemetry()
    if gpu:
        _log(f"GPU: {gpu.get('temp_c')}C | {gpu.get('power_w')}W | {gpu.get('clock_mhz')}MHz | fan {gpu.get('fan_pct')}%")
    _log(f"Output: {OUTPUT_DIR}")
    _log(f"Log: {LOG_FILE}")
    _log(f"NF4 cache: {'FOUND' if (NF4_CACHE_DIR / 'transformer' / 'config.json').exists() else 'NOT FOUND (first gen will be slow)'}")
    _log("=" * 60)

    if "--http" in sys.argv:
        _log("Mode: HTTP (port 8765)")
        mcp.run(transport="streamable_http", port=8765)
    else:
        _log("Mode: stdio (Claude Code)")
        mcp.run()
