"""
Environment Setup Script

Sets up the complete development environment:
1. Checks Python version
2. Creates virtual environment (optional)
3. Installs dependencies
4. Downloads ML models
5. Verifies installation

CLEAN and automated setup process.
"""

import sys
import subprocess
import platform
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def check_python_version():
    """Check if Python version is 3.10+."""
    print_header("Checking Python Version")

    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    print(f"Python version: {version_str}")
    print(f"Platform: {platform.system()} {platform.release()}")

    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("\n✗ Python 3.10+ is required!")
        print(f"  Current version: {version_str}")
        print("\nPlease upgrade Python:")
        print("  https://www.python.org/downloads/")
        return False

    print("✓ Python version is compatible!")
    return True


def check_venv_exists():
    """Check if virtual environment exists."""
    venv_dir = Path("venv")
    return venv_dir.exists()


def create_venv():
    """Create virtual environment."""
    print_header("Virtual Environment")

    if check_venv_exists():
        print("✓ Virtual environment already exists at: venv/")
        return True

    print("Creating virtual environment...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✓ Virtual environment created successfully!")
        print("\nTo activate it:")
        if platform.system() == "Windows":
            print("  venv\\Scripts\\activate")
        else:
            print("  source venv/bin/activate")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create virtual environment: {e}")
        return False


def get_pip_executable():
    """Get the correct pip executable path."""
    if check_venv_exists():
        if platform.system() == "Windows":
            return Path("venv/Scripts/pip.exe")
        else:
            return Path("venv/bin/pip")
    return "pip"


def install_dependencies():
    """Install Python dependencies from requirements.txt."""
    print_header("Installing Dependencies")

    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("✗ requirements.txt not found!")
        return False

    print("Installing packages from requirements.txt...")
    print("This may take several minutes...\n")

    pip_exe = get_pip_executable()

    try:
        # Upgrade pip first
        print("Upgrading pip...")
        subprocess.run(
            [str(pip_exe), "install", "--upgrade", "pip"],
            check=True,
            capture_output=False
        )

        # Install requirements
        print("\nInstalling requirements...")
        subprocess.run(
            [str(pip_exe), "install", "-r", "requirements.txt"],
            check=True,
            capture_output=False
        )

        print("\n✓ All dependencies installed successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed to install dependencies: {e}")
        print("\nTry installing manually:")
        print(f"  {pip_exe} install -r requirements.txt")
        return False


def download_models():
    """Download ML models."""
    print_header("Downloading ML Models")

    print("Running model download script...")

    try:
        python_exe = sys.executable
        if check_venv_exists():
            if platform.system() == "Windows":
                python_exe = "venv\\Scripts\\python.exe"
            else:
                python_exe = "venv/bin/python"

        subprocess.run(
            [python_exe, "scripts/download_models.py"],
            check=True,
            capture_output=False
        )
        return True

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed to download models: {e}")
        print("\nTry downloading manually:")
        print("  python scripts/download_models.py")
        return False


def verify_installation():
    """Verify that everything is installed correctly."""
    print_header("Verifying Installation")

    checks = {
        "gradio": False,
        "fastapi": False,
        "sentence_transformers": False,
        "pandas": False,
        "torch": False,
    }

    python_exe = sys.executable
    if check_venv_exists():
        if platform.system() == "Windows":
            python_exe = "venv\\Scripts\\python.exe"
        else:
            python_exe = "venv/bin/python"

    for package in checks.keys():
        try:
            result = subprocess.run(
                [python_exe, "-c", f"import {package}; print({package}.__version__)"],
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()
            print(f"✓ {package:25s} {version}")
            checks[package] = True
        except Exception:
            print(f"✗ {package:25s} NOT INSTALLED")
            checks[package] = False

    # Check model
    print("\nChecking ML model...")
    model_path = Path("client/models/KRTransformer")
    if model_path.exists() and any(model_path.iterdir()):
        print(f"✓ Korean BERT model found at: {model_path}")
    else:
        print(f"✗ Korean BERT model NOT FOUND at: {model_path}")
        checks["model"] = False

    all_good = all(checks.values())

    print("\n" + "=" * 60)
    if all_good:
        print("✓ ALL CHECKS PASSED!")
    else:
        print("✗ SOME CHECKS FAILED")
    print("=" * 60)

    return all_good


def main():
    """Main setup function."""

    print("\n" + "=" * 60)
    print("LocalizationTools - Environment Setup")
    print("=" * 60)
    print("\nThis script will set up your development environment.")
    print("It will:")
    print("  1. Check Python version")
    print("  2. Create virtual environment (optional)")
    print("  3. Install dependencies")
    print("  4. Download ML models")
    print("  5. Verify installation")

    # Step 1: Check Python version
    if not check_python_version():
        sys.exit(1)

    # Step 2: Virtual environment (optional)
    print("\n" + "=" * 60)
    use_venv = input("Create/use virtual environment? (recommended) [Y/n]: ").strip().lower()
    if use_venv != 'n':
        if not create_venv():
            print("\n⚠ Continuing without virtual environment...")

    # Step 3: Install dependencies
    if not install_dependencies():
        sys.exit(1)

    # Step 4: Download models
    if not download_models():
        print("\n⚠ Model download failed, but you can download it later.")
        print("  Run: python scripts/download_models.py")

    # Step 5: Verify
    verify_installation()

    # Final instructions
    print("\n" + "=" * 60)
    print("✓ SETUP COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    if check_venv_exists():
        print("\n1. Activate virtual environment:")
        if platform.system() == "Windows":
            print("   venv\\Scripts\\activate")
        else:
            print("   source venv/bin/activate")
    print("\n2. Run the client application:")
    print("   python client/main.py")
    print("\n3. Run the server (in another terminal):")
    print("   uvicorn server.main:app --host localhost --port 8888 --reload")
    print("\nFor more info, see README.md")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
