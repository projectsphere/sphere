@echo off
SETLOCAL

SET PYTHON_CMD=python

where python >nul 2>&1
IF NOT %ERRORLEVEL%==0 (
    where py >nul 2>&1
    IF %ERRORLEVEL%==0 (
        SET PYTHON_CMD=py
    ) ELSE (
        echo [Sphere Bot] Python is not installed or not added to PATH.
        echo Please install Python and ensure it's accessible via 'python' or 'py'.
        pause
        EXIT /B 1
    )
)

IF NOT EXIST "venv" (
    echo [Sphere Bot] Creating virtual environment...
    %PYTHON_CMD% -m venv venv
)

echo [Sphere Bot] Activating virtual environment...
call venv\Scripts\activate.bat

echo ------------------------------------------
echo [Sphere Bot] Virtual Environment Ready
echo ------------------------------------------

title Sphere Bot

echo [Sphere Bot] Installing/upgrading dependencies...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install setuptools
%PYTHON_CMD% -m pip install -r requirements.txt

echo [Sphere Bot] Starting bot...
%PYTHON_CMD% run.py

ENDLOCAL
pause
