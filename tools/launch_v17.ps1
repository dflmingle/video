$v17Path='C:/Users/89trillion/PveMontageShot01V17'
$existing=Get-NetTCPConnection -LocalPort 5257 -State Listen -ErrorAction SilentlyContinue
if (-not $existing) { Start-Process -FilePath 'C:/Program Files/nodejs/node.exe' -ArgumentList 'node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5257 --strictPort' -WorkingDirectory $v17Path -WindowStyle Hidden -RedirectStandardOutput ($v17Path+'/output/vite-v17.log') -RedirectStandardError ($v17Path+'/output/vite-v17-error.log') }
