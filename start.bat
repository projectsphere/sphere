@echo off
SETLOCAL

echo  ____            __
echo /\  _`\         /\ \
echo \ \,\L\_\  _____\ \ \___      __   _ __    __
echo  \/_\__ \ /\ '__`\ \  _ `\  /'__`\/\`'__\/'__`\
echo    /\ \L\ \ \ \L\ \ \ \ \ \/\  __/\ \ \//\  __/
echo    \ `\____\ \ ,__/\ \_\ \_\ \____\\ \_\\ \____\
echo     \/_____/\ \ \/  \/_/\/_/\/____/ \/_/ \/____/
echo              \ \_\
echo               \/_/

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

%PYTHON_CMD% setup.py

ENDLOCAL
pause
