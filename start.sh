#!/bin/bash

# Sphere Bot Startup Script for Unix-like systems (Linux/Mac)
# This script runs setup.py which handles all initialization and then starts the bot

set -e  # Exit on any error

echo ' ____            __'
echo '/\  _`\         /\ \'
echo '\ \,\L\_\  _____\ \ \___      __   _ __    __'
echo ' \/_\__ \ /\ '\''__\`\ \  _ `\  /'\''__`\/`'\''__\/'\''__\`\'
echo "   /\ \L\ \ \ \L\ \ \ \ \ \/\  __/\ \ \//\  __/"
echo "   \ \`\____\ \ ,__/\ \_\ \_\ \____\\\\ \_\\\\ \____\\"
echo "    \/_____/\ \ \/  \/_/\/_/\/____/ \/_/ \/____/"
echo "             \ \_\ "
echo "              \/_/"

# Determine Python command
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[Sphere Bot] Python is not installed or not in PATH."
    echo "[Sphere Bot] Please install Python and ensure it's accessible."
    exit 1
fi

$PYTHON_CMD setup.py
