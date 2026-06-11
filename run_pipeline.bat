@echo off
setlocal

if "%~1"=="" (
    echo Usage: run_pipeline.bat ^<input-root^>
    exit /b 2
)

echo === PPTX to DITA Migration Pipeline ===

echo [Stage 1] Snapshotting Word analysis sheets to PNG ...
python scripts\snapshot_analysis_docs.py --content-root %1
if errorlevel 1 goto error

echo [Stage 2] Extracting PPTX content into extracted.csv ...
python scripts\extract_to_csv.py --input-root %1 --out extracted.csv
if errorlevel 1 goto error

echo.
echo Review extracted.csv now. Press any key to continue with DITA generation.
pause > nul

echo [Stage 4] Generating DITA into dita\ ...
python scripts\generate_dita.py --csv extracted.csv --out dita\ --image-root %1
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
