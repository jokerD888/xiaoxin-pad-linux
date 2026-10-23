# 安装与首次启动

此教程面向 **TB-J716F + Android13/ZUI15 + Magisk** 的全新 Linux 安装。
`0.1.0-preview` 尚未完成第二台设备上的全新安装验收。
不要用安装脚本覆盖已经存在的 `/data/local/archlinux`；脚本会拒绝覆盖。

## 1. 准备文件

从夸克网盘 **「TB-J716F_ArchLinux_KDE桌面包」**（链接：[https://pan.quark.cn/s/dda7a083ddde](https://pan.quark.cn/s/dda7a083ddde)，提取码：`rrv5`，口令：`/~73f53bhDti~:/`）下载同一版本的 rootfs、Android 接入包、Anland 客户端 APK、daemon 模块、`AnlandTermux.apk` 和 `SHA256SUMS` 放入本地 `dist/` 目录。
（如果设备尚未解锁 Bootloader 或尚未 Root，请先阅读 [**从零开始全流程教程**](FULL_TUTORIAL_CN.md)。）

Windows 需要 Python 3、Git，以及 Android 官方 Platform Tools。
在 PowerShell 中确认 `adb devices` 只连接目标平板；多设备时使用你自己的 `-s` 序列号。
本项目不固定任何设备序列号。

先检查附件 SHA256，并运行：

```powershell
python scripts/windows/verify_release.py dist
```

验证脚本会检查压缩包内容和危险路径，不会执行安装脚本或自动刷机。
空间需容纳解压后的系统和归档文件；以该版本 manifest 的大小为准。

## 2. 安装 Android 端模块

将 `anland-daemon-0.1.0-preview.zip` 交给 Magisk 的“从本地安装”，完成后重启 Android。
使用项目提供的同版本模块；不是 Android ROM 刷机包。

将 `xiaoxin-host-0.1.0-preview.tar.xz`、rootfs 和 APK 推送到平板：

```powershell
adb push dist/xiaoxin-host-0.1.0-preview.tar.xz /data/local/tmp/
adb push dist/xiaoxin-rootfs-0.1.0-preview.tar.xz /data/local/tmp/
adb push dist/anland-linux-0.1.0-preview.apk /data/local/tmp/
adb shell
```

在 Android shell 内取得 Root 并解开接入包：

```sh
su
mkdir -p /data/local/tmp/xiaoxin-host
/data/adb/magisk/busybox tar -xJpf /data/local/tmp/xiaoxin-host-0.1.0-preview.tar.xz -C /data/local/tmp/xiaoxin-host
```

## 3. 全新安装

安装需要一个可交互终端，用于设置 **新的 Linux 用户密码**。不要把密码写在命令行参数中。
将下面 `ROOTFS_SHA256` 替换为 SHA256SUMS 内 rootfs 文件对应的 64 位十六进制值：

```sh
sh /data/local/tmp/xiaoxin-host/install.sh --allow-permissive \
  /data/local/tmp/xiaoxin-rootfs-0.1.0-preview.tar.xz \
  ROOTFS_SHA256 \
  /data/local/tmp/anland-linux-0.1.0-preview.apk
```

`--allow-permissive` 表示同意桌面启动时将 Android SELinux 切为 permissive。
本预览不宣称支持 enforcing；去掉标记不会得到一个已经验证的 enforcing 版本。
脚本不会修改现有 Android 应用或 SD 卡，也不会自动开启 KDE 开机自启。
如果原有客户端的签名与 Release 不同，APK 安装会失败；不会静默卸载它。

安装后手动启动桌面：

```sh
sh /data/adb/kde-desktop/bin/launch_kde_desktop.sh
```

如 Android 弹出应用权限/无障碍设置，按提示完成。物理键盘输入需要允许应用接收键盘事件。
旧版本客户端的设置不要整份导入，先使用本版提供的通用默认设置。

## 4. 终端模式

安装并打开一次 Termux 或兼容的 Anland Termux，再运行：

```sh
su -c 'sh /data/local/tmp/xiaoxin-host/configure-termux.sh'
```

重新打开 Termux 后进入相同 Arch Linux。此步骤在 Termux 的 `.bashrc` 加入带标记的入口，
不复制维护者的 Termux 配置或写死应用 UID。

Linux 内：

```sh
linux-mode terminal
linux-mode desktop
```

Konsole 新标签页使用持久终端；Ctrl+B 后按 W 选任务、按 C 新建任务。
切换会关闭图形应用，请先保存图形工作。未受保护的 Konsole 任务会阻止桌面退出。
终端中文按 Ctrl+空格，桌面中文可用 Shift 或 Ctrl+空格。

## 5. 可选配置

开机自启默认关闭。需要时执行接入包内 `set-autostart.sh on`；取消用 `off`。
Linux 密码、浏览器、应用账号和代理订阅由使用者自己配置。
不提供共享代理或预登录的 AGY、浏览器。
SD 卡配置由使用者另行处理，不运行母版 SD 转换脚本。

新机器首次使用时请检查 [验收范围](RELEASE.md)，尤其冷启动、录音停采、
键盘滚动和桌面/终端切换。失败时先关闭开机自启、返回 Android，保留日志用于定位。
