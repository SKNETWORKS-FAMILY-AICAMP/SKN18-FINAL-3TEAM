# 병렬 테스트 실행 스크립트 (PowerShell)
# 80개 조합을 8개 워커로 분할하여 병렬 처리

param(
    [int]$Limit = 0,
    [int]$SaveEvery = 10,
    [int]$NumWorkers = 8
)

Write-Host "Starting parallel test execution with $NumWorkers workers"
Write-Host "Limit: $Limit"
Write-Host "Save every: $SaveEvery"
Write-Host ""

$jobs = @()

# 각 워커를 백그라운드로 실행
for ($i = 0; $i -lt $NumWorkers; $i++) {
    Write-Host "Starting worker $i..."
    
    $logFile = "ragas_test_worker${i}.log"
    $scriptBlock = {
        param($workerId, $numWorkers, $limit, $saveEvery, $logFile)
        $output = python backend/ragas/fuseki/automated_test_runner.py `
            --limit $limit `
            --save-every $saveEvery `
            --worker-id $workerId `
            --num-workers $numWorkers 2>&1
        $output | Out-File -FilePath $logFile -Encoding utf8
        return $output
    }
    
    $job = Start-Job -ScriptBlock $scriptBlock -ArgumentList $i, $NumWorkers, $Limit, $SaveEvery, $logFile
    
    $jobs += $job
    Write-Host "Worker $i started (Job ID: $($job.Id), Log: $logFile)"
}

Write-Host ""
Write-Host "All workers started. Check logs: ragas_test_worker*.log"
Write-Host "Monitor progress:"
Write-Host "  Get-Job | Receive-Job"
Write-Host "  Get-Content ragas_test_worker*.log -Wait"
Write-Host ""
Write-Host "To check job status: Get-Job"
Write-Host "To stop all jobs: Get-Job | Stop-Job"
Write-Host "To remove all jobs: Get-Job | Remove-Job"

