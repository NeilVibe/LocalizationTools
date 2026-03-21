"""
LocaNext - Model2Vec Weight Downloader

Downloads the Model2Vec potion-multilingual-128M model for offline bundling.
Saves to models/Model2Vec/ directory which electron-builder includes in extraResources.

Usage:
    python tools/download_model2vec.py
    python tools/download_model2vec.py --output /custom/path
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Model2Vec weights for offline bundling")
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path(__file__).parent.parent / "models" / "Model2Vec"),
        help="Output directory for model files (default: models/Model2Vec)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)

    print(f"Downloading Model2Vec (~128MB)...")
    print(f"  Model: minishlab/potion-multilingual-128M")
    print(f"  Output: {output_dir}")

    try:
        from model2vec import StaticModel
    except ImportError:
        print("[ERROR] model2vec package not installed. Run: pip install model2vec")
        return 1

    try:
        model = StaticModel.from_pretrained("minishlab/potion-multilingual-128M")
    except Exception as e:
        print(f"[ERROR] Failed to download model: {e}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        model.save_pretrained(str(output_dir))
    except Exception as e:
        print(f"[ERROR] Failed to save model: {e}")
        return 1

    # Verify saved files
    config_path = output_dir / "config.json"
    if not config_path.exists():
        print(f"[ERROR] Verification failed: config.json not found in {output_dir}")
        return 1

    saved_files = list(output_dir.iterdir())
    print(f"\nSaved to {output_dir}/")
    for f in sorted(saved_files):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name} ({size_mb:.1f} MB)")

    print(f"\n[SUCCESS] Model2Vec weights saved ({len(saved_files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
