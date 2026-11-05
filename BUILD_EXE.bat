@echo off
cd /d "%~dp0"
py -3 -m pip install pyinstaller
if errorlevel 1 goto failed
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name BishoujoPromptMaker --add-data "defaults.json:." --add-data "models.json:." --add-data "translations.json:." app.py
if errorlevel 1 goto failed
echo Created: dist\BishoujoPromptMaker.exe
pause
exit /b
:failed
echo Build failed. See README.md.
pause

