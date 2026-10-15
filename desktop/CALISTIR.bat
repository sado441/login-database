@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
py -3 -m venv .venv
if not errorlevel 1 goto install
python -m venv .venv
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -m pip --version >nul 2>&1
if not errorlevel 1 goto dependencies
echo Sanal ortamda pip eksik. Python ensurepip ile hazirlaniyor...
".venv\Scripts\python.exe" -m ensurepip --upgrade
if errorlevel 1 goto pip_failed
:dependencies
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" app.py %*
if errorlevel 1 goto failed
exit /b 0
:pip_failed
echo.
echo Pip hazirlanamadi. Python kurulumundaki pip ve venv bilesenlerini kontrol edin.
echo Mevcut .venv klasorunu silmeden once hata mesajini paylasin.
pause
exit /b 1
:failed
echo.
echo Baslatilamadi. Yukaridaki hata mesajini kontrol edin.
echo Python 3.10 veya daha yeni bir surum ve tkinter gerekir.
pause
exit /b 1
