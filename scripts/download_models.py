"""
Download Required ML Models

Downloads the Korean BERT model directly to client/models/KRTransformer/
Simple, clean, visible - no hidden cache directories.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer
import os


def download_korean_bert_model():
    """Download Korean BERT model to local project folder."""

    # Target directory - visible in project
    models_dir = Path(__file__).parent.parent / "client" / "models"
    target_dir = models_dir / "KRTransformer"

    print("=" * 60)
    print("LocalizationTools - Model Download Script")
    print("=" * 60)
    print(f"\nTarget directory: {target_dir}")
    print(f"Models directory: {models_dir}")

    # Create models directory if it doesn't exist
    models_dir.mkdir(parents=True, exist_ok=True)

    # Check if model already exists
    if target_dir.exists() and any(target_dir.iterdir()):
        print("\n✓ Korean BERT model already exists!")
        print(f"  Location: {target_dir}")

        # Verify it loads
        try:
            print("\nVerifying model...")
            model = SentenceTransformer(str(target_dir))
            print("✓ Model loads successfully!")
            print(f"  Model type: {type(model)}")
            print(f"  Max sequence length: {model.max_seq_length}")
            return True
        except Exception as e:
            print(f"\n✗ Model exists but failed to load: {e}")
            print("  Downloading fresh copy...")

    # Download model
    print("\nDownloading Korean BERT model...")
    print("Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    print("(This is a multilingual model that works well with Korean)")
    print("\nThis may take a few minutes...")

    try:
        # Download model - it will be cached by sentence-transformers
        model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        model = SentenceTransformer(model_name)

        # Save to our local directory
        print(f"\nSaving model to: {target_dir}")
        model.save(str(target_dir))

        print("\n✓ Model downloaded and saved successfully!")
        print(f"  Location: {target_dir}")
        print(f"  Model type: {type(model)}")
        print(f"  Max sequence length: {model.max_seq_length}")

        # Test the model
        print("\nTesting model with sample Korean text...")
        test_text = "안녕하세요"  # "Hello" in Korean
        embedding = model.encode([test_text])
        print(f"✓ Model works! Generated {len(embedding[0])}-dimensional embedding")

        return True

    except Exception as e:
        print(f"\n✗ Error downloading model: {e}")
        print("\nTroubleshooting:")
        print("1. Check your internet connection")
        print("2. Make sure you have enough disk space (~400MB)")
        print("3. Try running: pip install --upgrade sentence-transformers")
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
