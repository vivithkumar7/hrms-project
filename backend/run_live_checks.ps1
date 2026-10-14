param(
    [string]$PythonPath = ".\.venv\Scripts\python.exe",
    [string]$NodeCommand = "npm",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$backendPath = $PSScriptRoot
$projectPath = Split-Path -Parent $backendPath
$deliverablesPath = Join-Path $projectPath "deliverables"
$pythonExecutable = if ([System.IO.Path]::IsPathRooted($PythonPath)) {
    $PythonPath
} else {
    Join-Path $backendPath $PythonPath
}
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw "Python interpreter not found: $pythonExecutable"
}

$environmentNames = @("DATABASE_URL", "JWT_SECRET_KEY", "UPLOAD_DIR", "CORS_ORIGINS")
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}

$runId = [Guid]::NewGuid().ToString("N")
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) "big-stack-live-checks-$runId"
$databasePath = (Join-Path $temporaryRoot "hrms-live.db").Replace("\", "/")
$uploadPath = Join-Path $temporaryRoot "uploads"
$stdoutPath = Join-Path $temporaryRoot "uvicorn.stdout.log"
$stderrPath = Join-Path $temporaryRoot "uvicorn.stderr.log"
$baseUrl = "http://127.0.0.1:$Port"
$server = $null

New-Item -ItemType Directory -Path $temporaryRoot -Force | Out-Null
New-Item -ItemType Directory -Path $deliverablesPath -Force | Out-Null

try {
    $env:DATABASE_URL = "sqlite:///$databasePath"
    $env:JWT_SECRET_KEY = "big-stack-live-checks-$runId-not-for-production"
    $env:UPLOAD_DIR = $uploadPath
    $env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"

    Push-Location $backendPath
    try {
        $pytestOutput = @(& $pythonExecutable -m pytest tests -q 2>&1)
        $pytestExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    $pytestText = $pytestOutput -join [Environment]::NewLine
    $pytestSummary = @($pytestOutput | Where-Object { "$_" -match "\d+ passed|\d+ failed|\d+ error" } | Select-Object -Last 1)

    Push-Location $projectPath
    try {
        $commandErrorPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $buildOutput = @(& $NodeCommand run build --prefix frontend 2>&1)
        $buildExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $commandErrorPreference
        Pop-Location
    }
    $buildText = $buildOutput -join [Environment]::NewLine
    $buildSummary = @($buildOutput | Where-Object { "$_" -match "built in|error during build" } | Select-Object -Last 1)
    if ($buildSummary.Count) {
        $buildSummary[0] = "$($buildSummary[0])" -replace "\x1B\[[0-?]*[ -/]*[@-~]", ""
    }

    $server = Start-Process `
        -FilePath $pythonExecutable `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port") `
        -WorkingDirectory $backendPath `
        -PassThru `
        -NoNewWindow `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath

    $healthResponse = $null
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if ($server.HasExited) {
            throw "API server exited early. See $stderrPath"
        }
        try {
            $healthResponse = Invoke-RestMethod -Uri "$baseUrl/api/health" -TimeoutSec 2
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $healthResponse -or $healthResponse.status -ne "ok") {
        throw "Live API did not become healthy. See $stderrPath"
    }

    $docsResponse = Invoke-WebRequest -Uri "$baseUrl/docs" -UseBasicParsing
    $redocResponse = Invoke-WebRequest -Uri "$baseUrl/redoc" -UseBasicParsing
    $openapiResponse = Invoke-WebRequest -Uri "$baseUrl/openapi.json" -UseBasicParsing
    $openapi = $openapiResponse.Content | ConvertFrom-Json
    $apiPaths = @($openapi.paths.PSObject.Properties | Where-Object { $_.Name.StartsWith("/api/") })
    $apiOperations = 0
    $securedOperations = 0
    foreach ($path in $apiPaths) {
        foreach ($operation in $path.Value.PSObject.Properties) {
            if ($operation.Name -in @("get", "post", "put", "patch", "delete", "options", "head")) {
                $apiOperations++
                if ($operation.Value.security) {
                    $securedOperations++
                }
            }
        }
    }

    $openapiPath = Join-Path $deliverablesPath "live-openapi.json"
    [System.IO.File]::WriteAllText(
        $openapiPath,
        ($openapi | ConvertTo-Json -Depth 100),
        [System.Text.UTF8Encoding]::new($false)
    )

    $pytestPassed = $pytestExitCode -eq 0
    $buildPassed = $buildExitCode -eq 0
    $docsPassed = $docsResponse.StatusCode -eq 200 -and $docsResponse.Content -match "swagger-ui"
    $redocPassed = $redocResponse.StatusCode -eq 200 -and $redocResponse.Content -match "redoc"
    $livePassed = $healthResponse.status -eq "ok" -and $docsPassed -and $redocPassed -and $apiOperations -gt 0
    $overallPassed = $pytestPassed -and $buildPassed -and $livePassed

    $results = [ordered]@{
        application = "Big Stack HRMS"
        generated_at = (Get-Date).ToString("o")
        overall = if ($overallPassed) { "PASS" } else { "FAIL" }
        backend_tests = [ordered]@{
            status = if ($pytestPassed) { "PASS" } else { "FAIL" }
            command = "python -m pytest tests -q"
            summary = if ($pytestSummary.Count) { "$($pytestSummary[0])".Trim() } else { "No pytest summary found" }
        }
        frontend_build = [ordered]@{
            status = if ($buildPassed) { "PASS" } else { "FAIL" }
            command = "npm run build --prefix frontend"
            summary = if ($buildSummary.Count) { "$($buildSummary[0])".Trim() } else { "No Vite build summary found" }
        }
        live_api = [ordered]@{
            status = if ($livePassed) { "PASS" } else { "FAIL" }
            base_url = $baseUrl
            health = $healthResponse.status
            swagger_ui_http = [int]$docsResponse.StatusCode
            redoc_http = [int]$redocResponse.StatusCode
            openapi_http = [int]$openapiResponse.StatusCode
            documented_api_paths = $apiPaths.Count
            documented_api_operations = $apiOperations
            bearer_protected_operations = $securedOperations
            openapi_file = "live-openapi.json"
        }
        note = "All automated checks use a temporary SQLite database and fictional test records. No configured HRMS database is changed."
    }
    $jsonPath = Join-Path $deliverablesPath "live-test-results.json"
    [System.IO.File]::WriteAllText(
        $jsonPath,
        ($results | ConvertTo-Json -Depth 10),
        [System.Text.UTF8Encoding]::new($false)
    )

    $statusColor = if ($overallPassed) { "#14785b" } else { "#b42318" }
    $pytestStatus = $results.backend_tests.status
    $buildStatus = $results.frontend_build.status
    $apiStatus = $results.live_api.status
    $pytestDetails = [System.Net.WebUtility]::HtmlEncode($results.backend_tests.summary)
    $buildDetails = [System.Net.WebUtility]::HtmlEncode($results.frontend_build.summary)
    $html = @"
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Big Stack HRMS live test report</title>
<style>
*{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#faf4fc,#fff8f3);color:#281c31;font:16px 'Segoe UI',Arial,sans-serif}
main{max-width:1020px;margin:56px auto;padding:0 28px}.brand{display:flex;align-items:center;gap:13px;color:#6e367d;font-weight:750;letter-spacing:.02em}
.mark{display:grid;place-items:center;width:46px;height:46px;border-radius:15px;background:linear-gradient(140deg,#fa9275,#ef6483 55%,#9465d0);color:white;font-size:23px}
h1{margin:35px 0 8px;font-size:36px;letter-spacing:-.04em}.sub{color:#786d7e}.overall{display:inline-block;margin:25px 0;padding:9px 16px;border-radius:20px;background:#e8f5ed;color:$statusColor;font-size:13px;font-weight:800;letter-spacing:.1em}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:17px}.card{min-height:170px;padding:22px;border:1px solid #eee4f0;border-radius:18px;background:#fff;box-shadow:0 12px 35px #41204f0b}
.card h2{margin:0 0 15px;font-size:15px}.status{font-size:11px;font-weight:800;letter-spacing:.1em;color:#14785b}.detail{margin-top:13px;color:#655a6d;font-size:14px;line-height:1.65}
.note{margin-top:23px;padding:15px 18px;border:1px solid #f0dfcf;border-radius:13px;background:#fff8ef;color:#775137;font-size:13px}
@media(max-width:760px){main{margin:24px auto;padding:0 17px}.grid{grid-template-columns:1fr}h1{font-size:29px}}
</style>
</head>
<body><main>
<div class="brand"><span class="mark">B</span><span>Big Stack People | Quality check</span></div>
<h1>Live system test report</h1>
<p class="sub">Generated $($results.generated_at). Full backend workflow suite, production frontend build, and live API documentation check.</p>
<div class="overall" style="color:$statusColor">OVERALL $($results.overall)</div>
<section class="grid">
<article class="card"><h2>Backend workflows</h2><div class="status">$pytestStatus</div><div class="detail">$pytestDetails</div><div class="detail">Authentication | employees | attendance | leave | payroll | reports | audit | notifications | OpenAPI</div></article>
<article class="card"><h2>Frontend production build</h2><div class="status">$buildStatus</div><div class="detail">$buildDetails</div><div class="detail">Vite production bundle completed.</div></article>
<article class="card"><h2>Live API &amp; Swagger</h2><div class="status">$apiStatus</div><div class="detail">Health: $($results.live_api.health)<br>Swagger UI: HTTP $($results.live_api.swagger_ui_http)<br>ReDoc: HTTP $($results.live_api.redoc_http)<br>OpenAPI operations: $($results.live_api.documented_api_operations)<br>Bearer-protected: $($results.live_api.bearer_protected_operations)</div></article>
</section>
<div class="note">Test records were created in a disposable SQLite database. The configured HRMS database and its employee/payroll data were not modified.</div>
</main></body></html>
"@
    $htmlPath = Join-Path $deliverablesPath "live-test-results.html"
    [System.IO.File]::WriteAllText($htmlPath, $html, [System.Text.UTF8Encoding]::new($false))

    Write-Output ($results | ConvertTo-Json -Depth 10)
    if (-not $overallPassed) {
        throw "Live checks failed. Review $jsonPath and the captured command output."
    }
} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    }
    foreach ($name in $environmentNames) {
        [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], "Process")
    }
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
