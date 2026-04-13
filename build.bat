@echo off
pip install -r requirements.txt
pyinstaller ^
  --onefile ^
  --noconsole ^
  --name Pigmato ^
  --add-data "ui;ui" ^
  main.py
echo.
echo Build finished. Output: dist\Pigmato.exe
pause
