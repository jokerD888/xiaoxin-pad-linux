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

## 性能调优与独占模式（MemAvailable 1.88 GB ➔ 2.53 GB）

本项目已全量合入最新的深度性能调优与独占运行模式，整机可用物理内存从原始基准 **1.88 GB** 跃升至 **2.53 GB**（**净赚 650MB+ 物理运行内存，增幅超 35%**）：

- **Android 宿主端深度精简**：内置 `scripts/android/debloat_android.sh`，无损拔除搜狗输入法 OEM 版、联想 OTA、用户体验遥测、系统推送等 22 个后台臃肿进程，开机 0 残留（支持一键恢复）。
- **Linux 独占模式与算力倾斜**：通过 cgroup v2 冰封 Android 用户层应用，限制宿主后台运行在小核（CPU 0-3），将骁龙 870 强悍的中核与超大核（3.2GHz）100% 专供 Linux 独占；锁定 Linux 关键进程为最高防御等级（`oom_score_adj -1000`），彻底免疫 LMK 杀进程。
- **KDE Plasma 6 桌面轻量化**：彻底停用 Baloo 文件语义索引器，关闭 KWin 毛玻璃模糊（Blur）与沉重动效，彻底根除空闲 CPU 偷跑、闪存频繁读写与移动端 GPU 渲染负担。
- **OLED 纯黑硬件级省电挂机**：内置 Wayland 原生 PyQt5 全屏黑屏框架（`black-screen-saver.py`），全屏 `#000000` 像素点硬件切断供电，兼顾防烧屏与极致省电；支持触控屏幕手势与任意键秒级无缝唤醒退出，挂机结束后进程退出，常驻物理内存 0 占用。
- 详细实测报告见：[**深度性能调优与极致轻量化指南**](docs/PERFORMANCE_TUNING.md) ｜ [Linux 独占模式说明](docs/LINUX_EXCLUSIVE_MODE.md)。

## 已整理的功能

- KDE Plasma / Wayland，Zink + Turnip，保留 90Hz。
- KWin 按实际损伤重绘；Anland 空闲等待新帧，避免 5 秒超时闪屏。
- PipeWire 扬声器与按需麦克风，原生音频线程空闲事件等待。
- 相机事件订阅及 I420 桥接，供浏览器等 Linux 应用使用。
- 中文拼音、实体键盘、Esc、触控板滚动及 Konsole 色彩预览设置。
- Konsole 与 Termux 共享 tmux；桌面退出后保留接入持久终端的命令行任务。
- 终端内中文候选，Ctrl+空格切换中英文。
- OLED 纯黑屏节能挂机桌面图标与触控唤醒。

## 快速入口

- [**从零开始：9008 解锁 BL、刷回 ZUI 15、Root 到安装 Linux 保姆级全流程教程**](docs/FULL_TUTORIAL_CN.md)
- [**深度性能调优与极致轻量化指南（MemAvailable 1.88G ➔ 2.53G）**](docs/PERFORMANCE_TUNING.md)
- [已 Root 设备安装与首次启动](docs/INSTALL.md)
- [Linux 独占模式深度说明与压测报告](docs/LINUX_EXCLUSIVE_MODE.md)
- [构建客户端、模块和干净镜像](docs/BUILD.md)
- [隐私边界与镜像生成方法](docs/PRIVACY.md)
- [发布文件、许可与验收范围](docs/RELEASE.md)
- [回退与常见问题](docs/TROUBLESHOOTING.md)

## 夸克网盘资源汇总（Linux 桌面一键包 / 解锁 BL / 官方底包 / Root 工具）

全流程所需的 **优化版 Arch Linux + KDE Wayland 桌面一键安装包**、**BL 解锁工具**、**ZUI 12.6 / ZUI 15 官方底包** 与 **Magisk Root 镜像** 已全部整理在夸克网盘（各目录文件详情见[全流程保姆级教程](docs/FULL_TUTORIAL_CN.md#一夸克网盘资源汇总与文件说明)）：

1. **「TB-J716F_ArchLinux_KDE桌面包」**（**核心包**：含 1.31 GiB 干净 `xiaoxin-rootfs`、一键安装脚本 `xiaoxin-host`、`anland-daemon` 模块、修复版 `anland-linux.apk`、`AnlandTermux.apk`、对应源码与 `SHA256SUMS`）
   - 链接：[https://pan.quark.cn/s/dda7a083ddde](https://pan.quark.cn/s/dda7a083ddde) ｜ 提取码：`rrv5` ｜ 口令：`/~73f53bhDti~:/`
2. **「小新pad pro 2021相关」**（含 ZUI 12.6 降级底包、ZUI 15.0.485 官方线刷包、9008 工具）
   - 链接：[https://pan.quark.cn/s/ba5e10d4736e](https://pan.quark.cn/s/ba5e10d4736e) ｜ 提取码：`TNwf` ｜ 口令：`/~3a353bPmPP~:/`
3. **「Android_A16_TB_J716F」**（含 9008/ADB 驱动、QPST/搞机通、BL 解锁替换镜像与 `sn.img`、ZUI 15 修补版 Magisk Boot 镜像）
   - 链接：[https://pan.quark.cn/s/5053a798cd6b](https://pan.quark.cn/s/5053a798cd6b) ｜ 提取码：`S2BM` ｜ 口令：`/~82dc3bPnL5~:/`

软件不包含母版设备的用户配置、账号、浏览器配置、聊天、代理订阅、密码、SSH 身份或代码。
浏览器、AGY 与代理由安装者自行安装和登录。首次配置生成新的系统身份和密码。

## 项目布局

```text
build/          干净 rootfs 导出、上游获取、客户端构建
docs/           全套从零安装教程、独占模式说明与性能调优指南
manifests/      上游版本、软件包和发布校验信息
patches/        Anland / KWin 源码修改
reports/        不含个人身份的检查结果
scripts/        Android 接入、Linux 服务、精简脚本与 Windows 部署工具
src/            自定义桥接、监控、黑屏屏保及客户端补丁
templates/      从零编写或审核的通用默认配置与快捷方式
dist/           本地 Release 附件；Git 默认忽略
```

## 上游与许可

Anland 上游：[SuperTurtleDev/anland](https://github.com/SuperTurtleDev/anland)，
基线提交见 [upstream.json](manifests/upstream.json)。保留上游版权与 GPLv3 许可。
镜像基于 Arch Linux ARM，属于社区适配项目，不是 Lenovo、Arch Linux 或 Anland 的官方发行版。
原有独立文件的许可证标识继续有效；第三方组件按各自许可证分发。

源码和教程可以单独发布。发布二进制时请同时提供对应源码、构建步骤、许可证及 SHA256，
不要将生成镜像或私钥提交到 Git 历史。[详细发布说明](docs/RELEASE.md)
