@echo off
setlocal

if "%~1"=="" (
    echo Usage: run_pipeline.bat ^<input-root^> [--stub-wav]
    echo   --stub-wav: copy %~dp0stock.wav in place of every real .wav
    echo               ^(testing aid for cross-system DITA transit^)
    exit /b 2
)

set STUB_ARG=
if /i "%~2"=="--stub-wav" set STUB_ARG=--stub-wav "%~dp0stock.wav"

echo === PPTX to DITA Migration Pipeline ===
if defined STUB_ARG echo ^(stub-wav mode: real .wav files will be replaced with stock.wav^)

echo [Stage 1] Normalising Word analysis sheets to PNG ...
python normalise_analysis_sheets.py --content-root %1
if errorlevel 1 goto error

echo [Stage 2] Extracting PPTX content into extracted.csv ...
python extract_to_csv.py --input-root %1 --out extracted.csv
if errorlevel 1 goto error

echo.
echo Review extracted.csv now. Press any key to continue with DITA generation.
pause > nul

echo [Stage 4] Generating DITA into dita\ ...
python generate_dita.py --csv extracted.csv --out dita\ --image-root %1 %STUB_ARG%
if errorlevel 1 goto error

goto end

:error
echo.
echo Pipeline failed. See extract.log / generate.log for details.
exit /b 1

:end
echo.
echo Pipeline complete. See dita\ for DITA topics and ditamaps.
exit /b 0
