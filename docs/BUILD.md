# 构建

工具需要 Python 3、Git。Android 客户端需要 JRE17、NDK r27d/API33、
Apktool 3.0.3 与 uber-apk-signer 1.3.0。客户端构建脚本拒绝不匹配的原 APK。
工具从其官方项目获取，不把本机 JRE、ADB、SDK、签名私钥装进仓库。

## Anland 源码与原生组件

```sh
python build/prepare_upstream.py
```

该脚本获取 pinned upstream commit 并应用 `patches/anland-desktop.patch`，
不会重置已有 checkout 或删除本地源码。
Windows PowerShell：

```powershell
./build/native.ps1 -NdkDir YOUR_NDK_PATH
```

也支持使用 `fetch_ndk_subset.py` 获取官方 r27d 中的最小工具集。
它按 HTTPS Range 下载、验证 ZIP 成员 CRC，不等于验证整个 NDK 归档的官方摘要。
从官方完整 SDK/NDK 构建更适合正式发布。

生成 `.build/libanland_consumer.so`、音频策略库和 `display_daemon`。
Release 构建不保留 DWARF 本地路径。音频策略通过当前 ROM 导出的内部函数
按进程禁用 MMAP；没有把 vendor `libaaudio.so` 放进项目或附件。
这是 Android13/ZUI15 适配，不保证所有系统版本都有该符号。

## Android 客户端

原 APK 对应来源与 SHA256 在 `manifests/base-apk.json`。
当前流程基于该 APK 解包并应用公开的 Smali 和 JNI 修改；
这不是直接运行 upstream Gradle 就能生成相同客户端的流程。
完整 upstream 源码、修改的 source patch 与 Smali 也随发布提供。
正式维护可将 Smali 改动移植回 Java/Gradle，需重新验证全部功能。

在项目外创建你自己的 `release.jks` 和密码文件，别复制别人的私钥。
然后传入工具路径和签名参数：

```powershell
./build/client.ps1 -SourceApk ORIGINAL.apk -Java JAVA.exe `
  -ApktoolJar apktool_3.0.3.jar -SignerJar uber-apk-signer-1.3.0.jar `
  -KeyStore OUTSIDE_PROJECT/release.jks -PasswordFile OUTSIDE_PROJECT/password.txt
python build/package_host.py
```

中间 APK 对齐后，以维护者自己的发行密钥重新签名；不发布调试签名中间件。
构建日志不要加入 Release 或 Git。

## Linux 自定义组件

`src/desktop` 提供相机桥接、终端 PTY、终端 Fcitx、宿主监控插件源代码。
在 Arch ARM 内使用 `cc` / `g++`、`pkg-config` 构建。
依赖分别为 PipeWire 开发头、Fcitx5Utils、Qt6/KCoreAddons/KSysGuardSystemStats。
源码中的原有独立许可证标识保持不变。

KWin 补丁位于上游 `producers/kde/anland_backend_Arch_v5` 后端。
二进制修补器只接受已知 KWin 6.7.4 SHA256，不用于任意其他版本。
基础镜像已经含补丁，不重复修补它。源码重建方式遵循对应上游 KDE 后端说明。

## 干净 rootfs

1. 在具有已验证运行环境的母版上准备 reviewed overlay：只打包 `scripts/linux` 和 `templates` 的普通文件。
2. 在母版 chroot 内以 Root 执行 `build/export_clean_rootfs.py`。
   `--stage` 必须是 `/var/tmp/xiaoxin-release-*` 下不存在的目录，
   `--output` 必须是新文件；已存在目录/文件会拒绝覆盖。
3. `--private-patterns` 可传入仓库之外保存的个人标识/凭据模式 JSON。
   模式不会写入镜像或 manifest。对运行母版不执行清理或原地修改。
4. 用 `scripts/windows/verify_release.py` 完整读取归档并校验。
   再在独立目录解压，验证包数据库、依赖、权限和第一次身份生成。
5. 全新设备验收之前将镜像标注为 preview。

没有安装包归档时，母版的 package-owned 配置检查只能覆盖 pacman 标记的 backup 文件。
其他程序文件来自已验证母版，须另做内容扫描和源代码/二进制对应审计。
该流程不宣称整个 rootfs 可逐字节可复现。
