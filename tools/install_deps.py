"""
LocaNext - Python Dependencies Installer

Installs all required Python packages for the backend server.
Uses pip to download and install packages.

IT-Friendly: This script is readable and transparent.
You can inspect exactly what it installs.

Packages installed:
- FastAPI + uvicorn (web server)
- torch (AI framework)
- transformers + sentence-transformers (NLP)
- pandas + openpyxl (Excel processing)
- SQLAlchemy + aiosqlite (database)
- And other required dependencies
"""

import subprocess
import sys
import os
from pathlib import Path


def get_pip_path():
    """Get path to pip in embedded Python."""
    script_dir = Path(__file__).parent
    python_dir = script_dir / "python"

    # Try Scripts folder first (Windows)
    pip_path = python_dir / "Scripts" / "pip.exe"
    if pip_path.exists():
        return str(pip_path)

    # Try python -m pip
    return None


def install_package(package, description=""):
    """Install a single package using pip."""
    print(f"\n[...] Installing {package}...")
    if description:
        print(f"      {description}")

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-warn-script-location", package],
        capture_output=False
    )

    if result.returncode != 0:
        print(f"[WARNING] Failed to install {package}")
        return False

    print(f"[OK] {package} installed")
    return True


def _is_light_mode() -> bool:
    """Check if --light flag or LOCANEXT_LIGHT_MODE env var is set."""
    if "--light" in sys.argv:
        return True
    if os.environ.get("LOCANEXT_LIGHT_MODE", "").lower() in ("1", "true", "yes"):
        return True
    return False


# Heavy ML packages skipped in light mode
_HEAVY_ML_PACKAGES = {"torch", "transformers", "sentence-transformers"}


def main():
    """Main function to install all dependencies."""
    light_mode = _is_light_mode()

    print("\n" + "=" * 50)
    if light_mode:
        print("  LocaNext - Python Dependencies Installer (LIGHT)")
    else:
        print("  LocaNext - Python Dependencies Installer")
    print("=" * 50)
    print("0%")  # Initial progress for UI
    sys.stdout.flush()

    # Core server dependencies
    packages = [
        # Web framework
        ("fastapi", "Web framework for API"),
        ("uvicorn[standard]", "ASGI server"),
        ("python-multipart", "File upload support"),
        ("python-socketio", "WebSocket support"),

        # Database
        ("sqlalchemy", "Database ORM"),
        ("psycopg2-binary", "PostgreSQL driver"),
        ("asyncpg", "Async PostgreSQL driver"),
        ("aiosqlite", "Async SQLite support"),

        # Authentication
        ("PyJWT", "JWT tokens (import jwt)"),
        ("python-jose[cryptography]", "JWT tokens (jose)"),
        ("passlib[bcrypt]", "Password hashing"),
        ("bcrypt", "Password hashing backend"),
        ("python-dotenv", "Environment variables"),

        # Validation
        ("pydantic", "Data validation"),
        ("pydantic-settings", "Settings management"),
        ("email-validator", "Email validation"),

        # Data processing
        ("pandas", "Data processing"),
        ("openpyxl", "Excel file support"),
        ("xlrd", "Legacy Excel support"),

        # HTTP client
        ("httpx", "HTTP client"),
        ("requests", "HTTP requests"),

        # Logging
        ("loguru", "Logging framework"),

        # AI/ML - THE BIG ONES
        ("torch", "PyTorch AI framework (~2GB)"),
        ("transformers", "Hugging Face transformers"),
        ("sentence-transformers", "Sentence embeddings"),
        ("model2vec", "Fast multilingual embeddings (Model2Vec)"),
        ("huggingface_hub", "Model downloading"),
        ("faiss-cpu", "Vector similarity search"),

        # Utilities
        ("tqdm", "Progress bars"),
        ("pyyaml", "YAML support"),
    ]

    # Light mode: skip heavy ML packages (torch, transformers, sentence-transformers)
    if light_mode:
        original_count = len(packages)
        packages = [(pkg, desc) for pkg, desc in packages if pkg not in _HEAVY_ML_PACKAGES]
        skipped = original_count - len(packages)
        print(f"[INFO] Light Mode: skipping {skipped} heavy ML packages (torch, transformers, sentence-transformers)")
        sys.stdout.flush()

    total = len(packages)
    print(f"\n[INFO] Will install {total} packages")
    if light_mode:
        print("[INFO] Light Mode install — this should be quick...\n")
    else:
        print("[INFO] This may take 15-20 minutes...\n")
    sys.stdout.flush()

    failed = []
    for i, (package, description) in enumerate(packages):
        # Calculate and print progress percentage
        progress = int((i / total) * 100)
        print(f"{progress}% - Installing {package}...")
        sys.stdout.flush()

        if not install_package(package, description):
            failed.append(package)

    print("100%")  # Complete
    print("\n" + "=" * 50)
    sys.stdout.flush()

    if failed:
        print(f"  [WARNING] {len(failed)} packages failed to install:")
        for pkg in failed:
            print(f"    - {pkg}")
        print("\n  The app may still work, but some features might be missing.")
        print("=" * 50)
        sys.stdout.flush()
        return 1

    print("  [SUCCESS] All dependencies installed!")
    print("=" * 50)
    print("\n  LocaNext backend is ready!")
    sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
