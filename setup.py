#!/usr/bin/env python3
"""
Sphere Bot Setup Script

This script handles the initial setup for the Sphere Discord bot:
- Creates a virtual environment
- Installs required dependencies
- Creates an interactive .env configuration file

Run this script once before starting the bot for the first time.
"""

import os
import sys
import subprocess
import platform
import webbrowser
import time
from pathlib import Path

# ANSI color codes
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_status(message):
    """Print a status message with colored Sphere Bot prefix."""
    print(f"{Colors.CYAN}[{Colors.BOLD}Sphere Bot{Colors.END}{Colors.CYAN}]{Colors.END} {message}")

def print_success(message):
    """Print a success message."""
    print(f"{Colors.GREEN}✓{Colors.END} {message}")

def print_warning(message):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.END} {message}")

def print_error(message):
    """Print an error message."""
    print(f"{Colors.RED}✗{Colors.END} {message}")

def run_command(command, description):
    """Run a shell command and return success status."""
    print_status(f"{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error during {description.lower()}: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False


def create_virtual_environment():
    """Create a Python virtual environment."""
    if os.path.exists("venv"):
        print_success("Virtual environment already exists")
        return True

    python_cmd = "python"
    if platform.system() == "Windows":
        # Try python first, then py
        try:
            subprocess.run(["python", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(["py", "--version"], check=True, capture_output=True)
                python_cmd = "py"
            except (subprocess.CalledProcessError, FileNotFoundError):
                print_error("Python is not installed or not accessible via 'python' or 'py'")
                print_error("Please install Python and ensure it's in your PATH")
                return False
    else:
        # On Unix-like systems, python3 might be the command
        try:
            subprocess.run(["python3", "--version"], check=True, capture_output=True)
            python_cmd = "python3"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    return run_command(f"{python_cmd} -m venv venv", "Creating virtual environment")


def activate_virtual_environment():
    """Get the path to the Python executable in the virtual environment."""
    if platform.system() == "Windows":
        python_exe = os.path.join("venv", "Scripts", "python.exe")
    else:
        python_exe = os.path.join("venv", "bin", "python")

    if not os.path.exists(python_exe):
        print_error("Virtual environment Python executable not found")
        print_error("Please ensure the virtual environment was created successfully")
        return None

    return python_exe


def install_dependencies(python_exe):
    """Install required Python packages."""
    print_status("Upgrading pip...")

    # Upgrade pip silently
    try:
        subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
                      check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print_warning(f"Could not upgrade pip: {e}")
        # Continue anyway

    if not run_command(f"{python_exe} -m pip install setuptools --quiet", "Installing setuptools"):
        return False

    print_status("Installing project dependencies...")
    print("This may take a moment...")

    # Show a simple progress indicator
    print("📦 Installing packages...")

    # Install requirements with quiet flag for cleaner output
    try:
        result = subprocess.run([python_exe, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
                               check=True, text=True)
        print_success("All dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False


def create_env_file():
    """Interactively create the .env configuration file."""
    env_file = Path(".env")

    if env_file.exists():
        print_success("Using existing .env file")
        return True

    print(f"\n{Colors.CYAN}[{Colors.BOLD}Sphere Bot{Colors.END}{Colors.CYAN}]{Colors.END} Creating .env configuration file...")
    print_status("Please provide the following configuration values:")

    # Open Discord Developer Portal first
    print_status("Opening Discord Developer Portal so you can create a bot and get your token...")
    try:
        browser_opened = webbrowser.open("https://discord.com/developers/applications")
        if browser_opened:
            print_success("Browser opened! Please create a new application and copy the bot token")
            print(f"{Colors.RED}Important: In the 'Bot' section, make sure to enable these Privileged Gateway Intents:{Colors.END}")
            print(f"{Colors.RED}  • Presence Intent{Colors.END}")
            print(f"{Colors.RED}  • Server Members Intent{Colors.END}")
            print(f"{Colors.RED}  • Message Content Intent{Colors.END}")
        else:
            print_warning("Browser may not have opened - please manually visit: https://discord.com/developers/applications")
    except Exception as e:
        print_warning(f"Could not open browser automatically: {e}")
        print_status("Please manually visit: https://discord.com/developers/applications")

    input(f"{Colors.CYAN}[{Colors.BOLD}Sphere Bot{Colors.END}{Colors.CYAN}]{Colors.END} Press Enter after you've created your bot application and copied the token...")

    # Required fields
    while True:
        bot_token = input(f"{Colors.CYAN}[{Colors.BOLD}Sphere Bot{Colors.END}{Colors.CYAN}]{Colors.END} Enter your Discord bot token: ").strip()
        if bot_token:
            break
        print_warning("Bot token is required!")

    bot_prefix = input(f"{Colors.CYAN}[{Colors.BOLD}Sphere Bot{Colors.END}{Colors.CYAN}]{Colors.END} Enter the bot command prefix (default: !): ").strip()
    if not bot_prefix:
        bot_prefix = "!"

    # Optional fields
    api_url = input(f"{Colors.CYAN}[{Colors.BOLD}Sphere Bot{Colors.END}{Colors.CYAN}]{Colors.END} Enter Banlist API URL (optional, press Enter to skip): ").strip()
    api_key = input(f"{Colors.CYAN}[{Colors.BOLD}Sphere Bot{Colors.END}{Colors.CYAN}]{Colors.END} Enter Banlist API Key (optional, press Enter to skip): ").strip()

    # Write the .env file
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(f"BOT_TOKEN={bot_token}\n")
            f.write(f"BOT_PREFIX={bot_prefix}\n")
            if api_url:
                f.write(f"API_URL={api_url}\n")
            if api_key:
                f.write(f"API_KEY={api_key}\n")

        print_success(f".env file created successfully at {env_file.absolute()}")
        return True
    except Exception as e:
        print_error(f"Error creating .env file: {e}")
        return False


def main():
    """Main setup function."""
    print(f"{Colors.CYAN}{'='*42}")
    print(f"{Colors.CYAN}{'     Sphere Bot Setup Script     '}")
    print(f"{Colors.CYAN}{'='*42}{Colors.END}")

    # Check if we're in the right directory
    if not Path("requirements.txt").exists():
        print_error("requirements.txt not found in current directory")
        print_error("Please run this script from the bot's root directory")
        sys.exit(1)

    # Step 1: Create virtual environment
    if not create_virtual_environment():
        print_error("Setup failed: Could not create virtual environment")
        sys.exit(1)

    # Step 2: Get Python executable from venv
    python_exe = activate_virtual_environment()
    if not python_exe:
        print_error("Setup failed: Could not find virtual environment Python")
        sys.exit(1)

    # Step 3: Install dependencies
    if not install_dependencies(python_exe):
        print_error("Setup failed: Could not install dependencies")
        sys.exit(1)

    # Step 4: Create .env file
    if not create_env_file():
        print_error("Setup failed: Could not create .env file")
        sys.exit(1)

    print(f"\n{Colors.GREEN}{'='*42}")
    print(f"{Colors.GREEN}{'        Setup Complete!          '}")
    print(f"{Colors.GREEN}{'='*42}{Colors.END}")
    print_status("Starting bot...")
    print(f"{Colors.CYAN}{'='*42}{Colors.END}")

    # Start the bot
    import subprocess
    import sys
    try:
        subprocess.run([python_exe, "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        # Run again with captured output to analyze the error
        try:
            result = subprocess.run([python_exe, "main.py"], capture_output=True, text=True)
            error_output = str(result.stderr) + str(result.stdout)
            if "Improper token has been passed" in error_output or "401 Unauthorized" in error_output or "LoginFailure" in error_output:
                print_error("Discord bot not found or invalid token")
                print_status("Removing invalid .env file - please run setup again")
                env_file = Path(".env")
                if env_file.exists():
                    env_file.unlink()
                sys.exit(1)
            else:
                print_error("Bot failed to start - check your configuration")
                print_status("Please ensure you have enabled all Privileged Gateway Intents in the Discord Developer Portal Bot section")
                sys.exit(1)
        except Exception:
            # Fallback if second run also fails
            print_error("Bot failed to start - check your configuration")
            print_status("Please ensure you have enabled all Privileged Gateway Intents in the Discord Developer Portal Bot section")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}[{Colors.BOLD}Sphere Bot{Colors.END}{Colors.CYAN}]{Colors.END} Bot stopped by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
