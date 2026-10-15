@echo off
setlocal
cd /d "%~dp0"
if not exist "drivers\Interception-1.0.1\install-interception.exe" (
 echo Once INTERCEPTION_HAZIRLA.bat dosyasini calistirin.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 echo Once INTERCEPTION_HAZIRLA.bat dosyasini calistirin.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" prepare_interception.py --verify-installer
if errorlevel 1 (
 echo Surucu dosyasi dogrulanamadi. Kurulum yapilmadi.
 pause
 exit /b 1
)
echo Interception surucusu kurulacak. Windows yonetici onayi isteyecek.
powershell -NoProfile -Command "$p = Start-Process -FilePath (Join-Path (Get-Location) 'drivers\Interception-1.0.1\install-interception.exe') -ArgumentList '/install' -Verb RunAs -Wait -PassThru; exit $p.ExitCode"
if errorlevel 1 (
 echo Kurulum basarisiz veya yonetici onayi verilmedi. Hata mesajini kontrol edin.
) else (
 echo Kurulum komutu tamamlandi. Windows'u yeniden baslatin.
)
pause
