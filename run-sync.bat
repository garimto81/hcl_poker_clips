@echo off
cd /d %~dp0
echo [%date% %time%] HCL Smart Sync Running...
node scripts/sync-hcl.js
echo [%date% %time%] Sync Completed
rem pause
