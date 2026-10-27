# B16 – Đăng ký / gỡ lịch chạy định kỳ trong Windows Task Scheduler (không cần quyền Administrator).
#   Đăng ký:  powershell -ExecutionPolicy Bypass -File scripts\dang_ky_lich.ps1
#   Chạy thử ngay:  Start-ScheduledTask -TaskName DropoutEWS-HangTuan
#   Xem kết quả:    Get-ScheduledTaskInfo -TaskName DropoutEWS-HangTuan   (LastTaskResult = 0 là thành công)
#   Gỡ:       powershell -ExecutionPolicy Bypass -File scripts\dang_ky_lich.ps1 -Go
param(
    [switch]$Go,
    [string]$Ngay = "Monday",     # thứ chạy hằng tuần
    [string]$Gio = "07:00"
)

$TaskName = "DropoutEWS-HangTuan"
if ($Go) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Output "Đã gỡ lịch ${TaskName}."
    exit 0
}

$Script = Join-Path $PSScriptRoot "chay_dinh_ky.ps1"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`"" -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Ngay -At $Gio
# Máy tắt đúng giờ hẹn thì chạy bù khi bật lại; giới hạn 1 giờ; chỉ chạy khi người dùng đã đăng nhập (Docker Desktop cần phiên đăng nhập).
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Hệ thống cảnh báo sớm bỏ học (B16): pipeline chấm điểm + sao lưu hằng tuần" -Force | Out-Null
Write-Output "Đã đăng ký ${TaskName}: ${Ngay} lúc ${Gio} hằng tuần."
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State
