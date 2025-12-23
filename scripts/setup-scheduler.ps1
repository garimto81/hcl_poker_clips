# HCL Video Smart Sync - 작업 스케줄러 자동 등록 스크립트
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$TaskName = "HCL_Video_Smart_Sync"
$TaskDescription = "매일 오전 8시 유튜브 최신 영상을 구글 시트와 스마트 동기화합니다."
$ActionPath = "c:\Antigravity\hcl_poker_clips\run-sync.bat"
$WorkingDirectory = "c:\Antigravity\hcl_poker_clips"

# 1. 작업 동작(Action) 정의
$Action = New-ScheduledTaskAction -Execute $ActionPath -WorkingDirectory $WorkingDirectory

# 2. 트리거(Trigger) 정의 - 매일 오전 8시
$Trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM

# 3. 설정(Settings) 정의 - 노트북 전원 연결 여부와 상관없이 실행
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 4. 기존 작업이 있다면 삭제 (업데이트를 위해)
Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false

# 5. 작업 등록
Register-ScheduledTask -Action $Action -Trigger $Trigger -TaskName $TaskName -Description $TaskDescription -Settings $Settings -RunLevel Highest

Write-Host "--------------------------------------------------" -ForegroundColor Cyan
Write-Host "✅ 작업 스케줄러 등록 완료!" -ForegroundColor Green
Write-Host "이름: $TaskName"
Write-Host "시간: 매일 오전 8:00"
Write-Host "대상: $ActionPath"
Write-Host "--------------------------------------------------" -ForegroundColor Cyan
Write-Host "이제 매일 아침 AI가 스마트 동기화를 수행합니다."
