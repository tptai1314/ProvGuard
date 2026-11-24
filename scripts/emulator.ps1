<#
.SYNOPSIS
    Quan ly vong doi Android Emulator cho ProvGuard (Tang 0 - C1).
.DESCRIPTION
    Cung cap cac thao tac:
      - start: khoi dong AVD (co ho tro chay ngam -NoWindow, tat animation)
      - wait: cho he thong boot hoan tat (sys.boot_completed = 1)
      - stop: tat emulator mot cach an toan (adb emu kill)
      - restart: khoi dong lai
      - save-snapshot: luu snapshot trang thai sach de tai su dung
      - load-snapshot: khoi phuc snapshot trang thai sach
      - status: kiem tra trang thai ket noi cua emulator
.EXAMPLE
    .\scripts\emulator.ps1 -Action start -AvdName Pixel_9
    .\scripts\emulator.ps1 -Action wait
    .\scripts\emulator.ps1 -Action stop
    .\scripts\emulator.ps1 -Action save-snapshot -SnapshotName clean_state
    .\scripts\emulator.ps1 -Action load-snapshot -SnapshotName clean_state
#>

[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [ValidateSet("start", "wait", "stop", "restart", "save-snapshot", "load-snapshot", "status")]
    [string]$Action = "status",

    [string]$AvdName = "Pixel_9",
    [string]$Device = "emulator-5554",
    [string]$SnapshotName = "clean_state",
    [switch]$NoWindow,
    [int]$TimeoutSeconds = 180
)

# Chuan bi PATH toi adb va emulator neu chua co
$SdkPath = $env:ANDROID_HOME
if (-not $SdkPath -or -not (Test-Path $SdkPath)) {
    $SdkPath = Join-Path $env:LOCALAPPDATA "Android\Sdk"
}
if (Test-Path $SdkPath) {
    $PlatformTools = Join-Path $SdkPath "platform-tools"
    $EmulatorDir = Join-Path $SdkPath "emulator"
    if ((Test-Path $PlatformTools) -and ($env:PATH -notlike "*$PlatformTools*")) { $env:PATH = "$PlatformTools;$env:PATH" }
    if ((Test-Path $EmulatorDir) -and ($env:PATH -notlike "*$EmulatorDir*")) { $env:PATH = "$EmulatorDir;$env:PATH" }
}

function Get-EmulatorStatus {
    $devices = & adb devices | Out-String
    if ($devices -match "$Device\s+device") {
        return "online"
    } elseif ($devices -match "$Device\s+offline") {
        return "offline"
    } elseif ($devices -match "$Device\s+bootloader") {
        return "bootloader"
    } else {
        return "not_found"
    }
}

function Wait-EmulatorBoot {
    param([int]$MaxWaitSec = 180)
    Write-Host "[INFO] Dang cho thiet bi $Device khoi dong..." -ForegroundColor Cyan
    $Elapsed = 0
    $CheckInterval = 3

    # Cho den khi adb nhan dien device
    while ($Elapsed -lt $MaxWaitSec) {
        $st = Get-EmulatorStatus
        if ($st -eq "online") { break }
        Start-Sleep -Seconds $CheckInterval
        $Elapsed += $CheckInterval
        Write-Host "  ... cho ket noi adb ($Elapsed/$MaxWaitSec giay, trang thai: $st)" -ForegroundColor DarkGray
    }

    if ((Get-EmulatorStatus) -ne "online") {
        Write-Host "[ERROR] Timeout cho ket noi adb toi $Device sau $MaxWaitSec giay!" -ForegroundColor Red
        return $false
    }

    # Cho den khi sys.boot_completed = 1
    Write-Host "[INFO] Thiet bi online. Cho he dieu hanh hoan tat boot (sys.boot_completed)..." -ForegroundColor Cyan
    while ($Elapsed -lt $MaxWaitSec) {
        $booted = (& adb -s $Device shell getprop sys.boot_completed 2>$null).Trim()
        if ($booted -eq "1") {
            Write-Host "[OK] Android boot hoan tat!" -ForegroundColor Green
            
            # Toi uu hoa moi truong: tat animation va mo khoa
            Write-Host "[INFO] Ap dung cau hinh toi uu cho ProvGuard..." -ForegroundColor Cyan
            & adb -s $Device shell settings put global window_animation_scale 0 2>$null
            & adb -s $Device shell settings put global transition_animation_scale 0 2>$null
            & adb -s $Device shell settings put global animator_duration_scale 0 2>$null
            & adb -s $Device shell settings put system screen_off_timeout 1800000 2>$null
            & adb -s $Device shell wm dismiss-keyguard 2>$null
            & adb -s $Device shell input keyevent 224 2>$null
            & adb -s $Device shell input swipe 540 1900 540 400 300 2>$null
            Write-Host "[OK] Da tat animations va mo khoa man hinh." -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds $CheckInterval
        $Elapsed += $CheckInterval
        Write-Host "  ... cho boot_completed ($Elapsed/$MaxWaitSec giay)" -ForegroundColor DarkGray
    }

    Write-Host "[ERROR] Timeout cho Android boot hoan tat sau $MaxWaitSec giay!" -ForegroundColor Red
    return $false
}

function Start-EmulatorProcess {
    $currentStatus = Get-EmulatorStatus
    if ($currentStatus -eq "online") {
        Write-Host "[WARN] Emulator $Device da dang chay o trang thai online." -ForegroundColor Yellow
        return $true
    }

    Write-Host "[INFO] Khoi dong AVD '$AvdName'..." -ForegroundColor Cyan
    $emuExe = (Get-Command emulator.exe -ErrorAction SilentlyContinue).Source
    if (-not $emuExe) {
        Write-Host "[ERROR] Khong tim thay emulator.exe trong PATH!" -ForegroundColor Red
        return $false
    }

    $emuArgs = @("-avd", $AvdName, "-no-boot-anim", "-netdelay", "none", "-accel", "on")
    if ($NoWindow) {
        $emuArgs += "-no-window"
        Write-Host "  Chay o che do khong hien thi cua so (-no-window)" -ForegroundColor DarkGray
    }

    Start-Process -FilePath $emuExe -ArgumentList $emuArgs -PassThru | Out-Null
    Write-Host "[OK] Tien trinh emulator da duoc kich hoat." -ForegroundColor Green

    return (Wait-EmulatorBoot -MaxWaitSec $TimeoutSeconds)
}

function Stop-EmulatorProcess {
    Write-Host "[INFO] Dang dung thiet bi $Device..." -ForegroundColor Cyan
    $status = Get-EmulatorStatus
    if ($status -eq "not_found") {
        Write-Host "[INFO] Emulator khong dang chay." -ForegroundColor DarkGray
        return $true
    }

    & adb -s $Device emu kill 2>$null | Out-Null
    Start-Sleep -Seconds 3

    $statusAfter = Get-EmulatorStatus
    if ($statusAfter -eq "not_found") {
        Write-Host "[OK] Emulator da tat an toan." -ForegroundColor Green
        return $true
    } else {
        Write-Host "[WARN] adb emu kill chua dung han, dang kill tien trinh qemu..." -ForegroundColor Yellow
        Get-Process -Name "qemu-system-*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Da dung emulator." -ForegroundColor Green
        return $true
    }
}

# -------------------------------------------------------------------------
# Dieu phoi hanh dong (Action Dispatcher)
# -------------------------------------------------------------------------
switch ($Action) {
    "status" {
        $st = Get-EmulatorStatus
        Write-Host "Trang thai $Device : " -NoNewline
        if ($st -eq "online") {
            Write-Host "ONLINE" -ForegroundColor Green
            $model = (& adb -s $Device shell getprop ro.product.model 2>$null).Trim()
            $api = (& adb -s $Device shell getprop ro.build.version.release 2>$null).Trim()
            Write-Host "  Model: $model (Android $api)" -ForegroundColor White
        } else {
            Write-Host $st.ToUpper() -ForegroundColor Yellow
        }
    }

    "start" {
        Start-EmulatorProcess
    }

    "wait" {
        Wait-EmulatorBoot -MaxWaitSec $TimeoutSeconds
    }

    "stop" {
        Stop-EmulatorProcess
    }

    "restart" {
        Stop-EmulatorProcess
        Start-Sleep -Seconds 2
        Start-EmulatorProcess
    }

    "save-snapshot" {
        Write-Host "[INFO] Luu snapshot '$SnapshotName' tren $Device..." -ForegroundColor Cyan
        $res = & adb -s $Device emu avd snapshot save $SnapshotName
        Write-Host "[OK] Ket qua luu snapshot: $res" -ForegroundColor Green
    }

    "load-snapshot" {
        Write-Host "[INFO] Nap snapshot '$SnapshotName' tren $Device..." -ForegroundColor Cyan
        $res = & adb -s $Device emu avd snapshot load $SnapshotName
        Write-Host "[OK] Ket qua nap snapshot: $res" -ForegroundColor Green
        & adb -s $Device shell settings put global window_animation_scale 0 2>$null
    }
}
