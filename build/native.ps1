param([Parameter(Mandatory=$true)][string]$NdkDir)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$toolchain = if (Test-Path (Join-Path $NdkDir 'toolchains/llvm/prebuilt/windows-x86_64')) { Join-Path $NdkDir 'toolchains/llvm/prebuilt/windows-x86_64' } else { $NdkDir }
$cc = Join-Path $toolchain 'bin/clang.exe'
$sysroot = Join-Path $toolchain 'sysroot'
if (!(Test-Path -LiteralPath $cc)) { throw 'NDK clang not found' }
$source = Join-Path $repo '.build/anland'
$jni = Join-Path $source 'consumers/anland_v5/android_consumer/app/src/main/jni'
New-Item -ItemType Directory -Force '.build' | Out-Null
$common = @('--target=aarch64-linux-android33', "--sysroot=$sysroot", '-O2', '-g0', '-mno-outline-atomics', '-nostdlib', '-Wl,--no-undefined', '-Wl,-s', "-ffile-prefix-map=$repo=/src/xiaoxin-pad-linux")
& $cc @common -fPIC -shared '-Wl,-soname,libanland_consumer.so' "-I$jni" "-I$source/libdisplay_consumer" "-I$source/common" "$jni/native_consumer.c" "$jni/native_audio.c" "$jni/camera_service.c" "$source/libdisplay_consumer/display_consumer.c" "$source/common/socket_utils.c" -o .build/libanland_consumer.so -landroid -llog -ldl -laaudio -lcamera2ndk -lmediandk -lc
if ($LASTEXITCODE) { throw 'Native consumer build failed' }
& $cc @common -fPIC -shared "-I$jni" src/desktop/anland-audio-policy.c -o .build/libanland_audiopolicy.so -ldl -llog -lc '-Wl,--no-as-needed' -laaudio
if ($LASTEXITCODE) { throw 'Audio policy build failed' }
$crt = Join-Path $sysroot 'usr/lib/aarch64-linux-android/33'
& $cc @common -fPIE -pie "$crt/crtbegin_dynamic.o" "-I$source/common" "-I$source/libdisplay_daemon" "$source/daemon/daemon.c" "$source/libdisplay_daemon/display_daemon.c" "$source/common/socket_utils.c" -o .build/display_daemon -lc "$crt/crtend_android.o"
if ($LASTEXITCODE) { throw 'Display daemon build failed' }
