"""
Download Korean BERT Model for LocaNext

Downloads snunlp/KR-SBERT-V40K-klueNLI-augSTS from Hugging Face.
Model size: ~447MB, download time: 5-10 minutes

Based on VRS-Manager pattern for consistent model management.
"""

import os
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer


def download_korean_bert_model():
    """
    Download Korean BERT model from Hugging Face.

    Saves to: ./models/kr-sbert/

    Returns:
        bool: True if successful, False otherwise
    """

    # Project root directory
    project_root = Path(__file__).parent.parent
    target_dir = project_root / "models" / "kr-sbert"

    print("=" * 70)
    print("LocaNext - Korean BERT Model Download")
    print("=" * 70)
    print("\nModel: snunlp/KR-SBERT-V40K-klueNLI-augSTS")
    print("Size: ~447MB")
    print(f"Target: {target_dir}")
    print("\nThis will take 5-10 minutes depending on your internet speed...")
    print()

    # Create directory if it doesn't exist
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {target_dir}")
    except Exception as e:
        print(f"✗ Failed to create directory: {e}")
        return False

    # Download model from Hugging Face
    try:
        print("\nDownloading model from Hugging Face...")
        print("(This may take several minutes...)\n")

        model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

        print("\nSaving model to local directory...")
        model.save(str(target_dir))

        print(f"✓ Model saved to: {target_dir}")

    except Exception as e:
        print(f"\n✗ Failed to download model: {e}")
        print("\nPossible issues:")
        print("  1. No internet connection")
        print("  2. Hugging Face Hub is down")
        print("  3. Insufficient disk space (~1GB needed)")
        print("\nTry again later or check your internet connection.")
        return False

    # Verify critical files exist
    print("\nVerifying downloaded files...")

    required_files = ['config.json', 'model.safetensors']
    missing_files = []

    for file in required_files:
        file_path = target_dir / file
        if file_path.exists():
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"  ✓ {file} ({file_size_mb:.1f} MB)")
        else:
            print(f"  ✗ {file} - MISSING!")
            missing_files.append(file)

    if missing_files:
        print(f"\n✗ ERROR: Missing required files: {', '.join(missing_files)}")
        print("Download may have failed. Please try again.")
        return False

    # List all downloaded files
    print("\nAll downloaded files:")
    file_count = 0
    total_size = 0
    for item in sorted(target_dir.rglob('*')):
        if item.is_file():
            file_count += 1
            size = item.stat().st_size
            total_size += size
            if file_count <= 15:  # Show first 15 files
                rel_path = item.relative_to(target_dir)
                size_mb = size / (1024 * 1024)
                print(f"  - {rel_path} ({size_mb:.2f} MB)")

    if file_count > 15:
        print(f"  ... and {file_count - 15} more files")

    total_size_mb = total_size / (1024 * 1024)
    print(f"\nTotal: {file_count} files, {total_size_mb:.1f} MB")

    print("\n" + "=" * 70)
    print("✓ MODEL DOWNLOAD COMPLETE!")
    print("=" * 70)
    print("\nThe Korean BERT model is ready to use.")
    print(f"Location: {target_dir}")
    print("\nFor FULL build (with AI features):")
    print("  - Model will be bundled automatically")
    print("  - Executable size: ~2GB")
    print("\nFor offline transfer:")
    print("  1. Copy the entire 'models/' folder")
    print("  2. Place it next to LocaNext.exe on the target machine")

    return True


def main():
    """Main execution function."""

    print("\nStarting model download...\n")

    # Check if sentence-transformers is installed
    try:
        import sentence_transformers
        print(f"✓ sentence-transformers v{sentence_transformers.__version__} installed\n")
    except ImportError:
        print("✗ ERROR: sentence-transformers not installed!")
        print("\nPlease install it first:")
        print("  pip install sentence-transformers")
        sys.exit(1)

    success = download_korean_bert_model()

    if success:
        print("\nYou can now:")
        print("  1. Run the application: python server/main.py")
        print("  2. Build executables with the model bundled")
        print("  3. Run tests: pytest tests/")
        sys.exit(0)
    else:
        print("\nModel download failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
