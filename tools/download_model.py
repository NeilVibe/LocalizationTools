"""
LocaNext - AI Model Downloader

Downloads Korean BERT model from Hugging Face.
Uses huggingface_hub library for safe, verified downloads.

IT-Friendly: This script is readable and transparent.
You can inspect exactly what it downloads and where.

Model: snunlp/KR-SBERT-V40K-klueNLI-augSTS
Size: ~447 MB
Target: ../models/kr-sbert/
"""

import os
import sys
from pathlib import Path


def get_target_dir():
    """Get model target directory (relative to this script)."""
    script_dir = Path(__file__).parent
    # Go up from tools/ to app root, then models/kr-sbert
    return script_dir.parent / "models" / "kr-sbert"


def check_existing():
    """Check if model already exists."""
    target = get_target_dir()
    config = target / "config.json"
    # Model can be either pytorch_model.bin or model.safetensors
    model_pt = target / "pytorch_model.bin"
    model_st = target / "model.safetensors"

    if config.exists() and (model_pt.exists() or model_st.exists()):
        print(f"[OK] Model already exists at: {target}")
        return True
    return False


def install_huggingface_hub():
    """Install huggingface_hub if not present."""
    try:
        import huggingface_hub
        print(f"[OK] huggingface_hub v{huggingface_hub.__version__} ready")
        return True
    except ImportError:
        print("[...] Installing huggingface_hub (first time only)...")
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "huggingface_hub"],
            capture_output=True
        )
        if result.returncode != 0:
            print("[ERROR] Failed to install huggingface_hub")
            return False
        print("[OK] huggingface_hub installed")
        return True


def download_model():
    """Download model from Hugging Face."""
    from huggingface_hub import snapshot_download

    target = get_target_dir()
    model_id = "snunlp/KR-SBERT-V40K-klueNLI-augSTS"

    print(f"\n[...] Downloading: {model_id}")
    print(f"[...] Target: {target}")
    print(f"[...] This may take 5-10 minutes...\n")

    try:
        # Create target directory
        target.mkdir(parents=True, exist_ok=True)

        # Download using official Hugging Face API
        snapshot_download(
            repo_id=model_id,
            local_dir=str(target),
            local_dir_use_symlinks=False
        )
        return True

    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        return False


def verify_download():
    """Verify model files exist."""
    target = get_target_dir()

    print("\n[...] Verifying download...")

    # Check config.json (required)
    config = target / "config.json"
    if config.exists():
        size_mb = config.stat().st_size / (1024 * 1024)
        print(f"  [OK] config.json ({size_mb:.1f} MB)")
    else:
        print(f"  [MISSING] config.json")
        return False

    # Check model file (either pytorch_model.bin or model.safetensors)
    model_pt = target / "pytorch_model.bin"
    model_st = target / "model.safetensors"

    if model_pt.exists():
        size_mb = model_pt.stat().st_size / (1024 * 1024)
        print(f"  [OK] pytorch_model.bin ({size_mb:.1f} MB)")
    elif model_st.exists():
        size_mb = model_st.stat().st_size / (1024 * 1024)
        print(f"  [OK] model.safetensors ({size_mb:.1f} MB)")
    else:
        print(f"  [MISSING] model file (pytorch_model.bin or model.safetensors)")
        return False

    return True


def main():
    """Main function."""
    print("\n" + "=" * 50)
    print("  LocaNext - AI Model Downloader")
    print("=" * 50)

    # Check if already downloaded
    if check_existing():
        print("\n[SUCCESS] Model is ready!")
        return 0

    # Install huggingface_hub if needed
    if not install_huggingface_hub():
        return 1

    # Download model
    if not download_model():
        return 1

    # Verify
    if not verify_download():
        return 1

    print("\n" + "=" * 50)
    print("  [SUCCESS] Model download complete!")
    print("=" * 50)
    print("\n  LocaNext AI features are now ready!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
