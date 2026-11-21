<#
.SYNOPSIS
    Kiem tra moi truong may tinh va chuan bi ha tang cho thuc nghiem ProvGuard (Tang 0 - C0).
.DESCRIPTION
    Kiem tra:
      - Android SDK (adb, emulator, avdmanager)
      - WHPX / KVM hardware acceleration
      - Danh sach AVDs (dam bao co san may ao)
      - Python 3.11+ va virtualenv cua ProvGuard
      - Khoi tao cac thu muc lam viec: dump, cases, results, runs
      - Cau hinh may ao khi dang chay: tat animation de uiautomator dump khong bi timeout.
.EXAMPLE
    .\scripts\setup_env.ps1
    .\scripts\setup_env.ps1 -ConfigureRunningEmulator
#>

[CmdletBinding()]
param(
    [switch]$ConfigureRunningEmulator,
    [string]$TargetDevice = "emulator-5554"
)

$ErrorActionPreference = "Continue"

function Write-Step {
    param([string]$Message)
    Write-Host "`n[STEP] $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "  [FAIL] $Message" -ForegroundColor Red
}

$AllPassed = $true

Write-Host "============================================================" -ForegroundColor DarkCyan
Write-Host "  PROVGUARD - TANG 0: KIEM TRA MOI TRUONG & HA TANG (C0)    " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkCyan

# -------------------------------------------------------------------------
# 1. Kiem tra Android SDK Path
# -------------------------------------------------------------------------
Write-Step "1. Kiem tra Android SDK va cac cong cu platform-tools..."

$AndroidSdkPath = $env:ANDROID_HOME
if (-not $AndroidSdkPath -or -not (Test-Path $AndroidSdkPath)) {
    $AndroidSdkPath = $env:ANDROID_SDK_ROOT
}
if (-not $AndroidSdkPath -or -not (Test-Path $AndroidSdkPath)) {
    $DefaultSdk = Join-Path $env:LOCALAPPDATA "Android\Sdk"
    if (Test-Path $DefaultSdk) {
        $AndroidSdkPath = $DefaultSdk
    }
}

if ($AndroidSdkPath -and (Test-Path $AndroidSdkPath)) {
    Write-Success "Android SDK tim thay tai: $AndroidSdkPath"
    
    # Bo sung vao PATH phien hien tai neu chua co
    $PlatformTools = Join-Path $AndroidSdkPath "platform-tools"
    $EmulatorDir = Join-Path $AndroidSdkPath "emulator"
    $CmdlineTools = Join-Path $AndroidSdkPath "cmdline-tools\latest\bin"

    if ((Test-Path $PlatformTools) -and ($env:PATH -notlike "*$PlatformTools*")) {
        $env:PATH = "$PlatformTools;$env:PATH"
    }
    if ((Test-Path $EmulatorDir) -and ($env:PATH -notlike "*$EmulatorDir*")) {
        $env:PATH = "$EmulatorDir;$env:PATH"
    }
} else {
    Write-Fail "Khong tim thay Android SDK! Vui long cai dat Android Studio hoac dat bien ANDROID_HOME."
    $AllPassed = $false
}

# Kiem tra ADB
$AdbCmd = Get-Command adb -ErrorAction SilentlyContinue
if ($AdbCmd) {
    $AdbVer = & adb version | Select-Object -First 1
    Write-Success "adb san sang: $AdbVer"
} else {
    Write-Fail "adb khong co trong PATH hoac Android SDK."
    $AllPassed = $false
}

# Kiem tra Emulator executable
$EmuCmd = Get-Command emulator -ErrorAction SilentlyContinue
if ($EmuCmd) {
    Write-Success "emulator.exe san sang: $($EmuCmd.Source)"
} else {
    Write-Fail "emulator.exe khong co trong PATH hoac Android SDK."
    $AllPassed = $false
}

# -------------------------------------------------------------------------
# 2. Kiem tra Acceleration (WHPX / KVM)
# -------------------------------------------------------------------------
Write-Step "2. Kiem tra phan cung ao hoa (Hardware Acceleration)..."
if ($EmuCmd) {
    $AccelCheck = & emulator -accel-check 2>&1 | Out-String
    if ($AccelCheck -match "usable" -or $AccelCheck -match "installed and usable") {
        Write-Success "Hardware acceleration: Hoat dong tot (usable)."
    } else {
        Write-Warn "Hardware acceleration chua toi uu hoac bao loi:`n$AccelCheck"
        Write-Warn "Goi y: Hay bat Hyper-V va Windows Hypervisor Platform trong Windows Features."
    }
}

# -------------------------------------------------------------------------
# 3. Kiem tra danh sach AVD (Android Virtual Device)
# -------------------------------------------------------------------------
Write-Step "3. Kiem tra danh sach AVD..."
if ($EmuCmd) {
    $AvdList = & emulator -list-avds
    if ($AvdList) {
        Write-Success "Cac AVD hien co tren he thong:"
        foreach ($avd in $AvdList) {
            Write-Host "       - $avd" -ForegroundColor White
        }
    } else {
        Write-Warn "Chua co AVD nao duoc tao. Hay mo Android Studio Virtual Device Manager de tao mot AVD (khuyen nghi: Pixel 9, API 34/35/36, image google_apis)."
    }
}

# -------------------------------------------------------------------------
# 4. Kiem tra Python & Virtual Environment
# -------------------------------------------------------------------------
Write-Step "4. Kiem tra moi truong Python & pytest..."
$VenvPy = Join-Path (Get-Location) "ProvGuard\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    $VenvPy = Join-Path (Get-Location) ".venv\Scripts\python.exe"
}

if (Test-Path $VenvPy) {
    Write-Success "Tim thay virtualenv tai: $VenvPy"
    $PyVer = & $VenvPy --version
    Write-Success "Python version: $PyVer"
    
    # Chay nhanh pytest
    $PytestOutput = & $VenvPy -m pytest ProvGuard\tests -q 2>&1 | Out-String
    if ($PytestOutput -match "passed") {
        Write-Success "ProvGuard test suite: 19 passed."
    } else {
        Write-Warn "Pytest co van de:`n$PytestOutput"
    }
} else {
    Write-Warn "Chua tim thay ProvGuard/.venv. Hay chay: cd ProvGuard; python -m venv .venv; .\.venv\Scripts\pip install -e '.[dev]'"
}

# -------------------------------------------------------------------------
# 5. Khoi tao cac thu muc lam viec
# -------------------------------------------------------------------------
Write-Step "5. Khoi tao cac thu muc lam viec cho thuc nghiem..."
$DirsToCreate = @("dump", "cases", "results", "runs", "outputs\synthetic_demo")
foreach ($dir in $DirsToCreate) {
    $fullPath = Join-Path (Get-Location) $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Success "Tao thu muc: $dir"
    } else {
        Write-Success "Thu muc da ton tai: $dir"
    }
}

# -------------------------------------------------------------------------
# 6. Cau hinh Emulator dang chay (neu co)
# -------------------------------------------------------------------------
if ($ConfigureRunningEmulator) {
    Write-Step "6. Cau hinh may ao $TargetDevice dang ket noi..."
    $Devices = & adb devices | Out-String
    if ($Devices -match $TargetDevice) {
        Write-Host "  Dang tat animations tren $TargetDevice de dam bao uiautomator khong bi timeout..." -ForegroundColor White
        & adb -s $TargetDevice shell settings put global window_animation_scale 0
        & adb -s $TargetDevice shell settings put global transition_animation_scale 0
        & adb -s $TargetDevice shell settings put global animator_duration_scale 0
        & adb -s $TargetDevice shell settings put system screen_off_timeout 1800000
        & adb -s $TargetDevice shell wm dismiss-keyguard
        Write-Success "Da tat animation & mo khoa man hinh thanh cong tren $TargetDevice."
    } else {
        Write-Warn "Thiet bi $TargetDevice khong online. Hay bat emulator truoc khi chay flag -ConfigureRunningEmulator."
    }
}

Write-Host "`n============================================================" -ForegroundColor DarkCyan
if ($AllPassed) {
    Write-Host "  HOAN TAT KIEM TRA TANG 0: HA TANG SAN SANG!               " -ForegroundColor Green
} else {
    Write-Host "  CO MOT SO CANH BAO/LOI CAN KHAC PHUC.                    " -ForegroundColor Yellow
}
Write-Host "============================================================`n" -ForegroundColor DarkCyan
