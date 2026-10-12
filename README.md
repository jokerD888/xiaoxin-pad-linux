# Xiaoxin Pad Linux

在联想小新 Pad Pro 2021（TB-J716F / 骁龙 870）上，通过 Android Root + Arch Linux ARM
chroot + Anland 使用 KDE Wayland 桌面和 Linux 终端。

本项目整理已在同型号实机上验证的修复，提供干净 rootfs 的构建方式、Android 接入脚本、
客户端源码补丁及安装教程。**当前版本为 `0.1.0-preview`：母版功能已验证，
干净镜像完成静态与隔离检查，尚未在第二台设备上完成全新安装及重启验收。**
请按预览版本发布，不标记为正式稳定版。

## 支持范围

- TB-J716F，ARM64，Android 13 / ZUI 15，已解锁并安装 Magisk。
- 安装目录固定为 `/data/local/archlinux`，预设 Linux 用户为 `linux` / UID 1000。
- 需要安装 Magisk Anland daemon 模块和配套 Android 客户端。
- 本预览沿用实机使用的 SELinux permissive 环境，安装时要求明确选择。
  Chromium 在该 chroot 中需要 `--no-sandbox`；这与常规 Linux 桌面的隔离条件不同。
- 本项目不刷 Android ROM、不自动 Root、不转换或格式化 SD 卡、不卸载 Android 应用。

## 已整理的功能

- KDE Plasma / Wayland，Zink + Turnip，保留 90Hz。
- KWin 按实际损伤重绘；Anland 空闲等待新帧，避免 5 秒超时闪屏。
- PipeWire 扬声器与按需麦克风，原生音频线程空闲事件等待。
- 相机事件订阅及 I420 桥接，供浏览器等 Linux 应用使用。
- 中文拼音、实体键盘、Esc、触控板滚动及 Konsole 色彩预览设置。
- Konsole 与 Termux 共享 tmux；桌面退出后保留接入持久终端的命令行任务。
- 终端内中文候选，Ctrl+空格切换中英文。

## 快速入口

- [**从零开始：9008 解锁 BL、刷回 ZUI 15、Root 到安装 Linux 保姆级全流程教程**](docs/FULL_TUTORIAL_CN.md)
- [已 Root 设备安装与首次启动](docs/INSTALL.md)
- [构建客户端、模块和干净镜像](docs/BUILD.md)
- [隐私边界与镜像生成方法](docs/PRIVACY.md)
- [发布文件、许可与验收范围](docs/RELEASE.md)
- [回退与常见问题](docs/TROUBLESHOOTING.md)

## 夸克网盘资源汇总（Linux 桌面一键包 / 解锁 BL / 官方底包 / Root 工具）

全流程所需的 **优化版 Arch Linux + KDE Wayland 桌面一键安装包**、**BL 解锁工具**、**ZUI 12.6 / ZUI 15 官方底包** 与 **Magisk Root 镜像** 已全部整理在夸克网盘（各目录文件详情见[全流程保姆级教程](docs/FULL_TUTORIAL_CN.md#一夸克网盘资源汇总与文件说明)）：

1. **「TB-J716F_ArchLinux_KDE桌面包」**（**核心包**：含 1.31 GiB 干净 `xiaoxin-rootfs`、一键安装脚本 `xiaoxin-host`、`anland-daemon` 模块、修复版 `anland-linux.apk`、`AnlandTermux.apk`、对应源码与 `SHA256SUMS`）
   - 链接：[https://pan.quark.cn/s/1249631c0930](https://pan.quark.cn/s/1249631c0930) ｜ 提取码：`rrv5` ｜ 口令：`/~9c6c3bPo8d~:/`
2. **「小新pad pro 2021相关」**（含 ZUI 12.6 降级底包、ZUI 15.0.485 官方线刷包、9008 工具）
   - 链接：[https://pan.quark.cn/s/ba5e10d4736e](https://pan.quark.cn/s/ba5e10d4736e) ｜ 提取码：`TNwf` ｜ 口令：`/~3a353bPmPP~:/`
3. **「Android_A16_TB_J716F」**（含 9008/ADB 驱动、QPST/搞机通、BL 解锁替换镜像与 `sn.img`、ZUI 15 修补版 Magisk Boot 镜像）
   - 链接：[https://pan.quark.cn/s/5053a798cd6b](https://pan.quark.cn/s/5053a798cd6b) ｜ 提取码：`S2BM` ｜ 口令：`/~82dc3bPnL5~:/`

软件不包含母版设备的用户配置、账号、浏览器配置、聊天、代理订阅、密码、SSH 身份或代码。
浏览器、AGY 与代理由安装者自行安装和登录。首次配置生成新的系统身份和密码。

## 项目布局

```text
build/          干净 rootfs 导出、上游获取、客户端构建
patches/        Anland / KWin 源码修改
scripts/        Android 接入、Linux 服务、Windows 部署工具
src/            自定义桥接、监控及客户端补丁
templates/      从零编写或审核的通用默认配置
manifests/      上游版本、软件包和发布校验信息
reports/        不含个人身份的检查结果
dist/           本地 Release 附件；Git 默认忽略
```

## 上游与许可

Anland 上游：[SuperTurtleDev/anland](https://github.com/SuperTurtleDev/anland)，
基线提交见 [upstream.json](manifests/upstream.json)。保留上游版权与 GPLv3 许可。
镜像基于 Arch Linux ARM，属于社区适配项目，不是 Lenovo、Arch Linux 或 Anland 的官方发行版。
原有独立文件的许可证标识继续有效；第三方组件按各自许可证分发。

源码和教程可以单独发布。发布二进制时请同时提供对应源码、构建步骤、许可证及 SHA256，
不要将生成镜像或私钥提交到 Git 历史。[详细发布说明](docs/RELEASE.md)
