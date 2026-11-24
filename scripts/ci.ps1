<#
.SYNOPSIS
Unified deterministic CI/CD entrypoint for local runs and GitHub Actions.

.DESCRIPTION
Provides discrete fail-fast stages (deps, lint, test, stage-models, build, package, smoke, all)
checking $LASTEXITCODE on every external command without fragile shell operator chains.
#>
[CmdletBinding()]
param(
    [ValidateSet("deps", "lint", "test", "stage-models", "build", "package", "smoke", "all")]
    [string]$Stage = "all",
    [string]$PythonExe = "",
    [string]$InnoSetupExe = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Invoke-Checked {
    param(
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][string]$Exe,
        [string[]]$ArgList = @()
    )
    Write-Host "=== [$Label] ==="
    Write-Host "-> $Exe $($ArgList -join ' ')"
    & $Exe @ArgList
    if ($LASTEXITCODE -ne 0) {
        throw "Step '$Label' failed with exit code $LASTEXITCODE"
    }
}

function Resolve-PythonExe {
    param([string]$Requested)
    if ($Requested) {
        if (-not (Test-Path $Requested)) {
            throw "Requested Python executable not found: $Requested"
        }
        return (Resolve-Path $Requested).Path
    }
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    throw "No Python 3.11 interpreter found (.venv\Scripts\python.exe or PATH)."
}

function Resolve-InnoSetupExe {
    param([string]$Requested)
    if ($Requested) {
        if (-not (Test-Path $Requested)) {
            throw "Requested ISCC executable not found: $Requested"
        }
        return (Resolve-Path $Requested).Path
    }
    $cmd = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    throw "Inno Setup 6 compiler (ISCC.exe) not found. Install Inno Setup 6 or pass -InnoSetupExe."
}

function Get-ProjectVersion {
    param([Parameter(Mandatory)][string]$Py)
    $ver = & $Py -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path(r'$RepoRoot\pyproject.toml').read_text(encoding='utf-8'))['project']['version'])"
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($ver)) {
        throw "Failed to read project version from pyproject.toml"
    }
    return $ver.Trim()
}

function Invoke-StageDeps {
    param([Parameter(Mandatory)][string]$Py)
    $lockFile = Join-Path $RepoRoot "requirements.lock"
    if (-not (Test-Path $lockFile)) {
        throw "Pinned lockfile not found: $lockFile"
    }
    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($uvCmd) {
        Invoke-Checked "Install locked dependencies (uv)" $uvCmd.Source @(
            "pip", "install", "--python", $Py, "--index-strategy", "unsafe-best-match",
            "--require-hashes", "-r", $lockFile
        )
        Invoke-Checked "Install package editable without extra resolution" $uvCmd.Source @(
            "pip", "install", "--python", $Py, "--no-deps", "-e", $RepoRoot
        )
    } else {
        Invoke-Checked "Install locked dependencies (pip)" $Py @(
            "-m", "pip", "install", "--require-hashes", "--no-deps", "-r", $lockFile
        )
        Invoke-Checked "Install package editable without extra resolution" $Py @(
            "-m", "pip", "install", "--no-deps", "-e", $RepoRoot
        )
    }
}

function Invoke-StageLint {
    param([Parameter(Mandatory)][string]$Py)
    Invoke-Checked "Ruff check" $Py @("-m", "ruff", "check", ".")
    Invoke-Checked "Ruff format check" $Py @("-m", "ruff", "format", "--check", ".")
    Invoke-Checked "Tracked Clean Architecture gate" $Py @(
        (Join-Path $RepoRoot "scripts\pre_commit_check.py")
    )
}

function Invoke-StageTest {
    param([Parameter(Mandatory)][string]$Py)
    $prevQt = $env:QT_QPA_PLATFORM
    $env:QT_QPA_PLATFORM = "offscreen"
    try {
        Invoke-Checked "Fast unit & IPC tests (partial coverage)" $Py @(
            "-m", "pytest", "-m", "not slow", "--cov=autosilenttrimmer",
            "--cov-report=", "--cov-fail-under=0"
        )
        Invoke-Checked "Slow media pipeline tests (appended coverage + fail_under)" $Py @(
            "-m", "pytest", "-m", "slow", "--cov=autosilenttrimmer", "--cov-append",
            "--cov-report=term-missing", "--cov-report=xml:coverage.xml"
        )
    } finally {
        $env:QT_QPA_PLATFORM = $prevQt
    }
}

function Invoke-StageModels {
    param([Parameter(Mandatory)][string]$Py)
    Invoke-Checked "Stage & SHA-256 verify offline AI models" $Py @(
        (Join-Path $RepoRoot "scripts\stage_offline_models.py")
    )
}

function Invoke-StageBuild {
    param([Parameter(Mandatory)][string]$Py)
    Invoke-Checked "Verify pinned offline models before bundling" $Py @(
        (Join-Path $RepoRoot "scripts\stage_offline_models.py"), "--verify"
    )
    Invoke-Checked "Generate license notices and SBOM" $Py @(
        (Join-Path $RepoRoot "packaging\manifests\notices_generator.py")
    )
    $env:INCLUDE_AI_BUNDLE = "1"
    Invoke-Checked "Build PyInstaller trim-shim.exe" $Py @(
        "-m", "PyInstaller", "--noconfirm", (Join-Path $RepoRoot "packaging\pyinstaller\shim.spec")
    )
    Invoke-Checked "Build PyInstaller Full AI AutoSilentTrimmer bundle" $Py @(
        "-m", "PyInstaller", "--noconfirm", (Join-Path $RepoRoot "packaging\pyinstaller\core.spec")
    )
}

function Invoke-StagePackage {
    param([Parameter(Mandatory)][string]$Py, [string]$RequestedIscc)
    $iscc = Resolve-InnoSetupExe -Requested $RequestedIscc
    $version = Get-ProjectVersion -Py $Py
    $issPath = Join-Path $RepoRoot "packaging\windows\installer.iss"
    Invoke-Checked "Compile Inno Setup installer" $iscc @($issPath)

    $installerPath = Join-Path $RepoRoot "dist\installer\TrimThisVideo-Setup-$version-win-x64.exe"
    if (-not (Test-Path $installerPath)) {
        throw "Expected installer executable not created: $installerPath"
    }
    $sizeBytes = (Get-Item $installerPath).Length
    $maxBytes = 2000000000
    $sizeMb = [math]::Round($sizeBytes / 1048576.0, 2)
    Write-Host "Installer built: $installerPath ($sizeBytes bytes / $sizeMb MB)"
    if ($sizeBytes -ge $maxBytes) {
        throw "Installer size ($sizeBytes bytes) exceeds Inno Setup 2 GB limit ($maxBytes bytes)"
    }
    $hash = (Get-FileHash -Path $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $shaPath = "$installerPath.sha256"
    "$hash *$([System.IO.Path]::GetFileName($installerPath))" | Set-Content -Path $shaPath -Encoding ASCII
    Write-Host "SHA256 written: $shaPath ($hash)"
}

function Invoke-StageSmoke {
    param([Parameter(Mandatory)][string]$Py)
    $frozenDir = Join-Path $RepoRoot "dist\AutoSilentTrimmer"
    Invoke-Checked "Verify frozen PyInstaller folder offline" $Py @(
        (Join-Path $RepoRoot "scripts\verify_frozen_offline.py"), "--exe-dir", $frozenDir
    )

    $version = Get-ProjectVersion -Py $Py
    $installerPath = Join-Path $RepoRoot "dist\installer\TrimThisVideo-Setup-$version-win-x64.exe"
    if (-not (Test-Path $installerPath)) {
        throw "Installer not found for silent install smoke test: $installerPath"
    }

    $nonce = [Guid]::NewGuid().ToString("N").Substring(0, 8)
    $tempInstallDir = Join-Path $env:TEMP "ast_smoke_install_$nonce"
    $tempDataDir = Join-Path $env:TEMP "ast_smoke_data_$nonce"
    try {
        Write-Host "=== [Silent-install Setup.exe into isolated temp dir] ==="
        $proc = Start-Process -FilePath $installerPath -ArgumentList @(
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/DIR=`"$tempInstallDir`"",
            "/TASKS=none"
        ) -Wait -PassThru
        if ($proc.ExitCode -ne 0) {
            throw "Silent installer exited with code $($proc.ExitCode)"
        }

        $installedCli = Join-Path $tempInstallDir "autosilenttrimmer-cli.exe"
        if (-not (Test-Path $installedCli)) {
            throw "Silent install failed to deploy $installedCli"
        }

        Invoke-Checked "Verify silent-installed application offline" $Py @(
            (Join-Path $RepoRoot "scripts\verify_frozen_offline.py"), "--exe-dir", $tempInstallDir
        )
    } finally {
        $uninstaller = Join-Path $tempInstallDir "unins000.exe"
        if (Test-Path $uninstaller) {
            Write-Host "-> Running silent uninstaller: $uninstaller"
            Start-Process -FilePath $uninstaller -ArgumentList @(
                "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"
            ) -Wait | Out-Null
        }
        if ((Test-Path $tempInstallDir) -or (Test-Path $tempDataDir)) {
            & $Py (Join-Path $RepoRoot "scripts\clean_install.py") `
                --install-dir $tempInstallDir `
                --data-dir $tempDataDir `
                --skip-shell `
                --purge-data | Out-Null
        }
    }
}

Push-Location $RepoRoot
try {
    $py = Resolve-PythonExe -Requested $PythonExe
    Write-Host "Using Python: $py"
    switch ($Stage) {
        "deps"         { Invoke-StageDeps -Py $py }
        "lint"         { Invoke-StageLint -Py $py }
        "test"         { Invoke-StageTest -Py $py }
        "stage-models" { Invoke-StageModels -Py $py }
        "build"        { Invoke-StageBuild -Py $py }
        "package"      { Invoke-StagePackage -Py $py -RequestedIscc $InnoSetupExe }
        "smoke"        { Invoke-StageSmoke -Py $py }
        "all" {
            Invoke-StageLint -Py $py
            Invoke-StageTest -Py $py
            Invoke-StageModels -Py $py
            Invoke-StageBuild -Py $py
            Invoke-StagePackage -Py $py -RequestedIscc $InnoSetupExe
            Invoke-StageSmoke -Py $py
        }
    }
    Write-Host "Stage '$Stage' completed successfully."
} finally {
    Pop-Location
}
