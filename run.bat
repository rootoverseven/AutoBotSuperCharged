@echo off
rem This batch file runs a Python script in the same directory

rem Find the directory of this batch file
set DIR=%~dp0

rem Run the Python script using the system-wide Python interpreter
python "%DIR%ui.py"

rem Pause the command window to view the output
pause
