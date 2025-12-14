"""
Verify Required ML Models

IMPORTANT: The Korean BERT model is ALREADY in the project at:
  client/models/KR-SBERT-V40K-klueNLI-augSTS/

This script just VERIFIES it exists and loads correctly.
NO download needed - model is already cloned in project directory.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer
import os


def verify_korean_bert_model():
    """
    Verify Korean BERT model exists in project and loads correctly.

    Model is ALREADY in project directory - no download needed.
    """

    # Model is already in project at this location
    models_dir = Path(__file__).parent.parent / "client" / "models"
    target_dir = models_dir / "KR-SBERT-V40K-klueNLI-augSTS"

    print("=" * 60)
    print("LocalizationTools - Model Verification")
    print("=" * 60)
    print(f"\nExpected location: {target_dir}")
    print("Note: Model is ALREADY in project - just verifying it works.")
    print()

    # Check if model exists
    if not target_dir.exists():
        print("✗ ERROR: Model directory not found!")
        print(f"  Expected: {target_dir}")
        print("\n  The model should already be in the project.")
        print("  Please check git repository - model may not have been cloned.")
        return False

    if not any(target_dir.iterdir()):
        print("✗ ERROR: Model directory is empty!")
        print(f"  Location: {target_dir}")
        return False

    print("✓ Model directory found!")
    print(f"  Location: {target_dir}")

    # Check key files
    key_files = ['model.safetensors', 'config.json', 'tokenizer.json', 'vocab.txt']
    missing = []
    for file in key_files:
        if not (target_dir / file).exists():
            missing.append(file)

    if missing:
        print(f"\n✗ ERROR: Missing files: {', '.join(missing)}")
        return False

    print("✓ All required files present")

    # Verify it loads
    try:
        print("\nLoading model...")
        model = SentenceTransformer(str(target_dir))
        print("✓ Model loaded successfully!")
        print(f"  Model type: {type(model).__name__}")
        print(f"  Max sequence length: {model.max_seq_length}")

        # Test the model
        print("\nTesting model with sample Korean text...")
        test_text = "안녕하세요"  # "Hello" in Korean
        embedding = model.encode([test_text])
        print(f"✓ Model works! Generated {len(embedding[0])}-dimensional embedding")

        return True

    except Exception as e:
        print(f"\n✗ Model exists but failed to load: {e}")
        print("\nTroubleshooting:")
        print("1. Model files may be corrupted - check git repository")
        print("2. Try: pip install --upgrade sentence-transformers")
        print("3. Check if transformers library is installed")
        return False


def main():
    """Main download function."""

    print("\nStarting model download process...\n")

    success = download_korean_bert_model()

    print("\n" + "=" * 60)
    if success:
        print("✓ MODEL DOWNLOAD COMPLETE!")
        print("=" * 60)
        print("\nThe Korean BERT model is ready to use.")
        print("Location: client/models/KRTransformer/")
        print("\nYou can now run the application:")
        print("  python client/main.py")
    else:
        print("✗ MODEL DOWNLOAD FAILED")
        print("=" * 60)
        print("\nPlease check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
