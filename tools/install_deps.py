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


def main():
    """Main function to install all dependencies."""
    print("\n" + "=" * 50)
    print("  LocaNext - Python Dependencies Installer")
    print("=" * 50)

    # Core server dependencies
    packages = [
        # Web framework
        ("fastapi", "Web framework for API"),
        ("uvicorn[standard]", "ASGI server"),
        ("python-multipart", "File upload support"),
        ("python-socketio", "WebSocket support"),

        # Database
        ("sqlalchemy", "Database ORM"),
        ("aiosqlite", "Async SQLite support"),

        # Authentication
        ("python-jose[cryptography]", "JWT tokens"),
        ("passlib[bcrypt]", "Password hashing"),
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

        # Utilities
        ("tqdm", "Progress bars"),
        ("pyyaml", "YAML support"),
    ]

    print(f"\n[INFO] Will install {len(packages)} packages")
    print("[INFO] This may take 15-20 minutes...\n")

    failed = []
    for package, description in packages:
        if not install_package(package, description):
            failed.append(package)

    print("\n" + "=" * 50)

    if failed:
        print(f"  [WARNING] {len(failed)} packages failed to install:")
        for pkg in failed:
            print(f"    - {pkg}")
        print("\n  The app may still work, but some features might be missing.")
        print("=" * 50)
        return 1

    print("  [SUCCESS] All dependencies installed!")
    print("=" * 50)
    print("\n  LocaNext backend is ready!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
