# B16 – Lần chạy định kỳ (Task Scheduler gọi script này): pipeline chấm điểm → sao lưu.
# Chạy tay để thử:  powershell -ExecutionPolicy Bypass -File scripts\chay_dinh_ky.ps1
# Mã thoát ≠ 0 khi có bước lỗi → Task Scheduler ghi "Last Run Result" khác 0x0.
# Log: logs\dinh_ky_<thời điểm>.log (UTF-8); chi tiết từng bước ở logs\pipeline\<run_id>.log.

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
New-Item -ItemType Directory -Force (Join-Path $Root "logs") | Out-Null
$Log = Join-Path $Root ("logs\dinh_ky_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))
$env:PYTHONIOENCODING = "utf-8"

function Write-Log($Message) {
    $line = "{0:yyyy-MM-dd HH:mm:ss}  {1}" -f (Get-Date), $Message
    Add-Content -Path $Log -Value $line -Encoding utf8
    Write-Output $line
}

# Chạy lệnh ngoài qua cmd để ghi stdout + stderr thẳng vào log (UTF-8), trả về mã thoát.
function Invoke-Logged($CommandLine) {
    cmd /c "$CommandLine >> `"$Log`" 2>&1"
    return $LASTEXITCODE
}

Write-Log "Bắt đầu lần chạy định kỳ"
# Docker Desktop phải đang chạy; bật lại các container nếu đang dừng.
if ((Invoke-Logged "docker info") -ne 0) {
    Write-Log "LỖI: Docker chưa chạy. Mở Docker Desktop rồi chạy lại."
    exit 3
}
Invoke-Logged "docker compose up -d" | Out-Null
Start-Sleep -Seconds 15   # chờ PostgreSQL / MongoDB / MLflow sẵn sàng

$Pipeline = Invoke-Logged "`"$Python`" -m src.ops.run_pipeline --trigger scheduled"
Write-Log "Pipeline kết thúc, mã $Pipeline"

# Sao lưu cả khi pipeline lỗi: trạng thái CSDL (kể cả dòng FAILED trong pipeline_runs) vẫn đáng giữ.
$Backup = Invoke-Logged "`"$Python`" -m src.ops.backup"
Write-Log "Sao lưu kết thúc, mã $Backup"

if ($Pipeline -ne 0) { exit $Pipeline }
exit $Backup
