#!/usr/bin/env python3
"""
Development script for Knowledge Gains
Run with: uv run scripts/dev.py [command]
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str = ""):
    """Run a command and handle errors"""
    if description:
        print(f"🚀 {description}")

    try:
        result = subprocess.run(cmd, check=True, cwd=Path(__file__).parent.parent)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"Error: {e}")
        return False


def serve():
    """Start the development server"""
    print("🏋️ Starting Knowledge Gains development server...")
    run_command(
        ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
        "Starting FastAPI server with hot reload",
    )


def test():
    """Run tests"""
    run_command(["pytest", "-v"], "Running tests")


def format_code():
    """Format code with black and isort"""
    run_command(["black", "."], "Formatting code with black")
    run_command(["isort", "."], "Organizing imports with isort")


def lint():
    """Run linting checks"""
    run_command(["flake8", "."], "Running flake8 linting")
    run_command(["mypy", "."], "Running mypy type checking")


def check():
    """Run all checks (format, lint, test)"""
    print("🔍 Running all checks...")
    success = True
    success &= run_command(["black", "--check", "."], "Checking code formatting")
    success &= run_command(
        ["isort", "--check-only", "."], "Checking import organization"
    )
    success &= run_command(["flake8", "."], "Running linting")
    success &= run_command(["mypy", "."], "Running type checking")
    success &= run_command(["pytest", "-v"], "Running tests")

    if success:
        print("✅ All checks passed!")
    else:
        print("❌ Some checks failed!")
        sys.exit(1)


def setup():
    """Setup development environment"""
    print("🛠️ Setting up Knowledge Gains development environment...")

    # Create necessary directories
    dirs = ["uploads", "static/css", "static/js", "templates/components", "tests"]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {dir_path}")

    # Copy environment file if it doesn't exist
    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists() and env_example.exists():
        env_file.write_text(env_example.read_text())
        print("📝 Created .env file from .env.example")
        print("⚠️  Please update .env with your actual API keys and configuration")

    print("✅ Development environment setup complete!")
    print("\n📋 Next steps:")
    print("1. Update .env with your API keys")
    print("2. Set up your Supabase database")
    print("3. Run: uv run scripts/dev.py serve")


def db_migrate():
    """Run database migrations"""
    print("🗄️ Running database migrations...")
    print("Please run the SQL schema manually in your Supabase dashboard:")
    print("📄 File: database/schema.sql")


def install_hooks():
    """Install pre-commit hooks"""
    run_command(["pre-commit", "install"], "Installing pre-commit hooks")


def main():
    parser = argparse.ArgumentParser(description="Knowledge Gains development tools")
    parser.add_argument(
        "command",
        choices=[
            "serve",
            "test",
            "format",
            "lint",
            "check",
            "setup",
            "db-migrate",
            "install-hooks",
        ],
        help="Command to run",
    )

    args = parser.parse_args()

    commands = {
        "serve": serve,
        "test": test,
        "format": format_code,
        "lint": lint,
        "check": check,
        "setup": setup,
        "db-migrate": db_migrate,
        "install-hooks": install_hooks,
    }

    commands[args.command]()


if __name__ == "__main__":
    main()
