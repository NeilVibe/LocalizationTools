"""
LocaNext - Embedding Model Downloader

Downloads Qwen Embedding model from Hugging Face.
Uses sentence_transformers for optimal download and save.

IT-Friendly: This script is readable and transparent.
You can inspect exactly what it downloads and where.

Model: Qwen/Qwen3-Embedding-0.6B
Size: ~1.21 GB
Target: ../models/qwen-embedding/

P20 Migration: All tools unified to Qwen (XLSTransfer, KR Similar, LDM)
"""

import os
import sys
from pathlib import Path


# Model configuration (P20: Unified Qwen model)
MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
MODEL_DIR_NAME = "qwen-embedding"


def get_target_dir():
    """Get model target directory (relative to this script).

    In dev:      tools/download_model.py -> ../models/
    In packaged: resources/tools/download_model.py -> ../../models/
    """
    script_dir = Path(__file__).parent
    parent = script_dir.parent

    # Detect packaged app: parent is 'resources' folder
    if parent.name == "resources":
        # Packaged: go up two levels (resources/tools -> app root)
        app_root = parent.parent
    else:
        # Dev: go up one level (tools -> project root)
        app_root = parent

    return app_root / "models" / MODEL_DIR_NAME


def check_existing():
    """Check if model already exists."""
    target = get_target_dir()
    config = target / "config.json"
    # Model can be either pytorch_model.bin or model.safetensors
    model_pt = target / "pytorch_model.bin"
    model_st = target / "model.safetensors"

    if config.exists() and (model_pt.exists() or model_st.exists()):
        print(f"[OK] Embedding model already exists at: {target}")
        return True
    return False


def install_sentence_transformers():
    """Install sentence_transformers if not present."""
    try:
        import sentence_transformers
        print(f"[OK] sentence_transformers v{sentence_transformers.__version__} ready")
        return True
    except ImportError:
        print("[...] Installing sentence_transformers (first time only)...")
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "sentence-transformers"],
            capture_output=True
        )
        if result.returncode != 0:
            print("[ERROR] Failed to install sentence_transformers")
            return False
        print("[OK] sentence_transformers installed")
        return True


def download_model():
    """Download model from Hugging Face using sentence_transformers."""
    from sentence_transformers import SentenceTransformer
    import threading
    import time

    target = get_target_dir()

    print("0%")  # Initial progress
    print(f"\n[...] Downloading: {MODEL_ID}")
    print(f"[...] Target: {target}")
    print(f"[...] Size: ~1.21 GB")
    print(f"[...] This may take 5-15 minutes...\n")
    sys.stdout.flush()

    # Track progress in a separate thread
    download_complete = threading.Event()
    download_error = [None]

    def progress_tracker():
        """Print progress while downloading."""
        progress = 5
        while not download_complete.is_set() and progress < 95:
            print(f"{progress}%")
            sys.stdout.flush()
            time.sleep(5)  # Update every 5 seconds (larger model)
            progress = min(progress + 5, 95)

    def do_download():
        try:
            # Create target directory
            target.mkdir(parents=True, exist_ok=True)

            # Download using sentence_transformers (handles caching properly)
            print("[...] Loading model from Hugging Face...")
            sys.stdout.flush()
            model = SentenceTransformer(MODEL_ID)

            # Save to local directory
            print("[...] Saving model to local directory...")
            sys.stdout.flush()
            model.save(str(target))

        except Exception as e:
            download_error[0] = e
        finally:
            download_complete.set()

    # Start progress tracker
    tracker = threading.Thread(target=progress_tracker, daemon=True)
    tracker.start()

    # Start download
    downloader = threading.Thread(target=do_download)
    downloader.start()
    downloader.join()

    if download_error[0]:
        print(f"\n[ERROR] Download failed: {download_error[0]}")
        sys.stdout.flush()
        return False

    print("100%")
    sys.stdout.flush()
    return True


def verify_download():
    """Verify model files exist."""
    target = get_target_dir()

    print("\n[...] Verifying download...")

    # Check config.json (required)
    config = target / "config.json"
    if config.exists():
        size_kb = config.stat().st_size / 1024
        print(f"  [OK] config.json ({size_kb:.1f} KB)")
    else:
        print(f"  [MISSING] config.json")
        return False

    # Check model file (either pytorch_model.bin or model.safetensors)
    model_pt = target / "pytorch_model.bin"
    model_st = target / "model.safetensors"

    if model_st.exists():
        size_mb = model_st.stat().st_size / (1024 * 1024)
        print(f"  [OK] model.safetensors ({size_mb:.1f} MB)")
    elif model_pt.exists():
        size_mb = model_pt.stat().st_size / (1024 * 1024)
        print(f"  [OK] pytorch_model.bin ({size_mb:.1f} MB)")
    else:
        print(f"  [MISSING] model file (model.safetensors or pytorch_model.bin)")
        return False

    return True


def main():
    """Main function."""
    print("\n" + "=" * 50)
    print("  LocaNext - Embedding Model Downloader")
    print("=" * 50)

    # Check if already downloaded
    if check_existing():
        print("\n[SUCCESS] Embedding model is ready!")
        return 0

    # Install sentence_transformers if needed
    if not install_sentence_transformers():
        return 1

    # Download model
    if not download_model():
        return 1

    # Verify
    if not verify_download():
        return 1

    print("\n" + "=" * 50)
    print("  [SUCCESS] Embedding model download complete!")
    print("=" * 50)
    print("\n  LocaNext embedding features are now ready!")
    print(f"  Model: {MODEL_ID}")
    print(f"  Features: 100+ languages, 1024-dim embeddings")

    return 0


if __name__ == "__main__":
    sys.exit(main())
