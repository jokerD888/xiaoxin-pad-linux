param(
    [Parameter(Mandatory=$true)][string]$SourceApk,
    [Parameter(Mandatory=$true)][string]$Java,
    [Parameter(Mandatory=$true)][string]$ApktoolJar,
    [Parameter(Mandatory=$true)][string]$SignerJar,
    [Parameter(Mandatory=$true)][string]$KeyStore,
    [Parameter(Mandatory=$true)][string]$PasswordFile,
    [string]$Python='python'
)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
Set-Location $repo
if ([IO.Path]::GetFullPath($KeyStore).StartsWith($repo+[IO.Path]::DirectorySeparatorChar)) { throw 'Keep the signing private key outside the project.' }
foreach ($p in @('.build/libanland_consumer.so','.build/libanland_audiopolicy.so')) { if (!(Test-Path -LiteralPath $p)) { throw 'Run native.ps1 first.' } }
$lock=Get-Content manifests/base-apk.json -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $SourceApk -Algorithm SHA256).Hash.ToLowerInvariant() -ne $lock.sha256) { throw 'Source APK does not match the verified patch base.' }
if (Test-Path -LiteralPath '.build/apk/decoded') { throw 'Use a clean build directory; refusing to overwrite decoded sources.' }
New-Item -ItemType Directory -Force '.build/apk','dist' | Out-Null
& $Java -jar $ApktoolJar d $SourceApk -o .build/apk/decoded
if ($LASTEXITCODE) { throw 'Decode failed' }
& $Python -X utf8 build/patch_client.py
if ($LASTEXITCODE) { throw 'Patch failed' }
& $Java -jar $ApktoolJar b .build/apk/decoded -o .build/anland-unsigned.apk
if ($LASTEXITCODE) { throw 'APK build failed' }
& $Java -jar $SignerJar --apks .build/anland-unsigned.apk --out .build/aligned
if ($LASTEXITCODE) { throw 'Alignment failed' }
$aligned=(Get-ChildItem .build/aligned -Filter '*.apk' | Select-Object -First 1).FullName
& $Java -cp $SignerJar com.android.apksigner.ApkSignerTool sign --ks $KeyStore --ks-key-alias xiaoxin-linux --ks-pass "file:$PasswordFile" --out dist/anland-linux-0.1.0-preview.apk $aligned
if ($LASTEXITCODE) { throw 'Release signing failed' }
& $Java -cp $SignerJar com.android.apksigner.ApkSignerTool verify --verbose --print-certs dist/anland-linux-0.1.0-preview.apk
if ($LASTEXITCODE) { throw 'Signature verification failed' }
