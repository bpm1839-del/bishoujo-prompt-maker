@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 app.py
if errorlevel 1 pause
exit /b
:usepython
python app.py
if errorlevel 1 (
 echo Python 3.10 or later with Tcl/Tk is required. See README.md.
 pause
)
