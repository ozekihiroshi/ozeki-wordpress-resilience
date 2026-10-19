$ErrorActionPreference = 'Stop'
$source = '\\wsl.localhost\Ubuntu-24.04\home\ozeki\.local\share\owr-trust\key-20261018'
$usb = 'E:\owr-recovery\key-20261018'
if (!(Test-Path -LiteralPath (Join-Path $usb 'pin.json'))) { throw 'Expected USB files missing' }
if ((Get-FileHash (Join-Path $usb 'pin.json')).Hash -ne (Get-FileHash (Join-Path $source 'pin.json')).Hash) { throw 'USB trust pin mismatch' }
if (Test-Path -LiteralPath (Join-Path $usb 'private.encrypted.pem')) {
 Write-Host 'Existing encrypted backup found. Skipping encryption; retrying USB recovery verification.'
} else {
 if (Test-Path -LiteralPath (Join-Path $source 'export.encrypted.pem')) { throw 'Local encrypted export exists without USB copy. Inspect before proceeding.' }
 Write-Host 'Enter a new USB backup passphrase twice. Input is hidden. Keep it separately from the USB.'
 wsl -d Ubuntu-24.04 -- bash -lc 'set -eu; umask 077; cd /home/ozeki/.local/share/owr-trust/key-20261018; test ! -e export.encrypted.pem; openssl pkcs8 -topk8 -in private.pem -out export.encrypted.pem -v2 aes-256-cbc -iter 600000'
 if ($LASTEXITCODE -ne 0) { throw 'Encryption failed; no USB key copied' }
 Copy-Item -LiteralPath (Join-Path $source 'export.encrypted.pem') -Destination (Join-Path $usb 'private.encrypted.pem')
}
if ((Get-FileHash (Join-Path $source 'export.encrypted.pem')).Hash -ne (Get-FileHash (Join-Path $usb 'private.encrypted.pem')).Hash) { throw 'Encrypted backup hash mismatch' }
Copy-Item -LiteralPath (Join-Path $usb 'private.encrypted.pem') -Destination (Join-Path $source 'usb-readback.encrypted.pem')
Write-Host 'Enter the ORIGINAL encryption passphrase (not a new one). Input is hidden; do not press Enter before typing it.'
wsl -d Ubuntu-24.04 -- bash -lc 'set -eu; umask 077; cd /home/ozeki/.local/share/owr-trust/key-20261018; openssl dgst -sha256 -sign usb-readback.encrypted.pem -out usb-readback.sig approval.json; openssl dgst -sha256 -verify public.pem -signature usb-readback.sig approval.json'
if ($LASTEXITCODE -ne 0) { throw 'USB recovery signing test failed. Backup is NOT verified.' }
$report = [ordered]@{ kind='encrypted_usb_key_recovery'; passed=$true; checked_at=[DateTime]::UtcNow.ToString('o'); encrypted_key_sha256=(Get-FileHash (Join-Path $usb 'private.encrypted.pem')).Hash; test='Signature created with USB-readback encrypted key verified against original public key' }
$report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $usb 'recovery-test.json') -Encoding utf8
$report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $source 'usb-recovery-test.json') -Encoding utf8
Write-Host 'PASS: encrypted key copied and USB recovery signing verified. Safely eject the USB and store it offline.' -ForegroundColor Green
