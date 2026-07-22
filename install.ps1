param(
    [ValidateSet("codex", "claude", "agents")]
    [string]$Target = "codex",
    [string]$Version = "v1.0.0",
    [switch]$Update,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Repo = "fsbtactic-code/pishi-normalno"
$Asset = "pishi-normalno.zip"

function Get-PythonCommand {
    $Python = Get-Command python -ErrorAction SilentlyContinue
    if ($Python) {
        return @{
            Executable = $Python.Source
            Prefix = @()
        }
    }
    $Launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($Launcher) {
        return @{
            Executable = $Launcher.Source
            Prefix = @("-3")
        }
    }
    throw "Python 3.10 or newer is required."
}

function Invoke-SkillInstall {
    param([string]$SkillDir)

    $PythonCommand = Get-PythonCommand
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONDONTWRITEBYTECODE = "1"
    $Arguments = @("$SkillDir\scripts\cli.py", "install", "--target", $Target)
    if ($Update) {
        $Arguments += "--update"
    }
    if ($DryRun) {
        $Arguments += "--dry-run"
    }
    & $PythonCommand.Executable @($PythonCommand.Prefix) @Arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$LocalSkill = $null
if ($PSScriptRoot) {
    $Candidate = Join-Path $PSScriptRoot "skills\pishi-normalno"
    if (Test-Path -LiteralPath (Join-Path $Candidate "SKILL.md")) {
        $LocalSkill = $Candidate
    }
}

if ($LocalSkill) {
    Invoke-SkillInstall -SkillDir $LocalSkill
    exit 0
}

$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("pishi-normalno-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $TempRoot | Out-Null
try {
    $BaseUrl = "https://github.com/$Repo/releases/download/$Version"
    $ArchivePath = Join-Path $TempRoot $Asset
    $ChecksumPath = Join-Path $TempRoot "checksums.txt"
    Invoke-WebRequest -Uri "$BaseUrl/$Asset" -OutFile $ArchivePath
    Invoke-WebRequest -Uri "$BaseUrl/checksums.txt" -OutFile $ChecksumPath

    $ChecksumLine = Get-Content -LiteralPath $ChecksumPath -Encoding utf8 |
        Where-Object { $_ -match "\s+pishi-normalno\.zip$" } |
        Select-Object -First 1
    if (-not $ChecksumLine) {
        throw "Archive checksum is missing."
    }
    $Expected = ($ChecksumLine -split "\s+")[0].ToLowerInvariant()
    $Actual = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Expected -ne $Actual) {
        throw "Archive checksum mismatch."
    }

    $Extracted = Join-Path $TempRoot "extracted"
    Expand-Archive -LiteralPath $ArchivePath -DestinationPath $Extracted
    $DownloadedSkill = Join-Path $Extracted "pishi-normalno"
    if (-not (Test-Path -LiteralPath (Join-Path $DownloadedSkill "SKILL.md"))) {
        throw "Release archive has an invalid structure."
    }
    Invoke-SkillInstall -SkillDir $DownloadedSkill
} finally {
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force
    }
}
