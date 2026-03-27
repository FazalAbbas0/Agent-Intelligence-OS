[CmdletBinding(SupportsShouldProcess = $true)]
Param(
    [string]$TaskName = "AgentIntelligenceNotionSync",
    [string]$DailyAt = "09:00",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$runnerScript = Join-Path $PSScriptRoot "run_sync.ps1"

if (-not (Test-Path $runnerScript)) {
    throw "Runner script not found: $runnerScript"
}

$timeOfDay = [DateTime]::ParseExact($DailyAt, "HH:mm", $null)

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runnerScript`" -ProjectRoot `"$projectRoot`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs
$trigger = New-ScheduledTaskTrigger -Daily -At $timeOfDay
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing -and -not $Force) {
    throw "Task '$TaskName' already exists. Re-run with -Force to replace it."
}

if ($existing -and $Force) {
    if ($PSCmdlet.ShouldProcess($TaskName, "Unregister existing scheduled task")) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
}

if ($PSCmdlet.ShouldProcess($TaskName, "Register scheduled task")) {
    $registerParams = @{
        TaskName = $TaskName
        Action = $action
        Trigger = $trigger
        Principal = $principal
        Settings = $settings
    }
    Register-ScheduledTask @registerParams | Out-Null
}

Write-Host "Scheduled task '$TaskName' is configured."
Write-Host "Runs daily at $DailyAt."
Write-Host "Manual test command: Start-ScheduledTask -TaskName '$TaskName'"
