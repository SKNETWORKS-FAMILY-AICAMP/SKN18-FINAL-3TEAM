@echo off
REM 병렬 테스트 실행 스크립트 (Windows Batch)
REM 80개 조합을 8개 워커로 분할하여 병렬 처리

set NUM_WORKERS=8
set LIMIT=%1
set SAVE_EVERY=%2

if "%LIMIT%"=="" set LIMIT=0
if "%SAVE_EVERY%"=="" set SAVE_EVERY=10

echo Starting parallel test execution with %NUM_WORKERS% workers
echo Limit: %LIMIT%
echo Save every: %SAVE_EVERY%
echo.

REM 각 워커를 백그라운드로 실행
for /L %%i in (0,1,%NUM_WORKERS%-1) do (
    echo Starting worker %%i...
    start "Worker %%i" /B python backend/ragas/fuseki/automated_test_runner.py --limit %LIMIT% --save-every %SAVE_EVERY% --worker-id %%i --num-workers %NUM_WORKERS% ^> ragas_test_worker%%i.log 2^>^&1
    echo Worker %%i started
)

echo.
echo All workers started. Check logs: ragas_test_worker*.log
echo.
echo To check running processes: tasklist ^| findstr python
echo To stop all workers: taskkill /F /IM python.exe /FI "WINDOWTITLE eq Worker*"

