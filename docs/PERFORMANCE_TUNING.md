# 小新 Pad Pro 2021 深度性能调优与极致轻量化指南

> **设备型号**: 联想小新 Pad Pro 2021 (TB-J716F, Snapdragon 870, 6GB LPDDR5 RAM)  
> **系统架构**: Android 11 / 13 Host (ZUI 15) + Arch Linux ARM Chroot + KDE Plasma 6 (Wayland)  
> **调优效果**: 系统可用内存 (`MemAvailable`) 从基线 **1.88 GB** 跃升至 **2.53 GB**（**净赚 650MB+ 真实物理内存，增幅达 35%**），同时消除 CPU 偷跑、发热降频，整机续航与流畅度显著提升。

---

## 一、 性能调优架构图

```
┌────────────────────────────────────────────────────────────────────────┐
│                          TB-J716F 整机硬件资源                          │
│             (8核高通骁龙 870: 4小核 + 3中核 + 1超大核 | 6GB 物理运存)     │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
    【Android Host 端深度优化】              【Linux Chroot 端体验调优】
 ┌──────────────────────────────────┐ ┌──────────────────────────────────┐
 │ 1. 用户层彻底精简 22 个冗余包      │ │ 1. 彻底干掉 Baloo 索引器         │
 │    (斩除搜狗输入法/OTA/遥测等)     │ │    (杜绝单核 CPU 飙高与闪存磨损)  │
 │                                  │ │                                  │
 │ 2. Linux 独占模式深度冻结         │ │ 2. 剥离 KWin 毛玻璃与重特效      │
 │    (cgroup 冻结后台、禁用桌面)   │ │    (关闭 Blur/Contrast/缩放动效) │
 │                                  │ │                                  │
 │ 3. CPU 算力倾斜 (cpuset 隔离)    │ │ 3. OLED 纯黑硬件级省电挂机       │
 │    (Android 锁 0-3 / Linux 畅享) │ │    (全黑像素断电，触控秒唤醒)    │
 │                                  │ │                                  │
 │ 4. Linux 关键服务 OOM 豁免       │ │ 4. 0 常驻挂机进程内存占用        │
 │    (oom_score_adj = -1000)       │ │    (唤醒后自动退出回收全部资源)  │
 └──────────────────────────────────┘ └──────────────────────────────────┘
```

---

## 二、 内存优化里程碑数据实测

在整机运行 KDE Plasma 6 完整 Wayland 桌面（含任务栏、托盘、触控手势、网络与音频栈）的状态下，实测可用物理内存 (`MemAvailable`) 变化走势如下：

| 阶段 / 操作 | 可用物理内存 (`MemAvailable`) | 物理内存收益 | 关键动作与机制 |
| :--- | :--- | :--- | :--- |
| **优化前（原始基线）** | **1.88 GB** | 0 MB (基准) | Android 后台常驻 150+ 进程，ZRAM 积压 2.4GB，KDE 开启毛玻璃动效 |
| **第一阶段：Android 遥测精简** | **2.05 GB** | **+170 MB** | 彻底卸载 21 个联想/高通系统遥测、推广推送与冗余系统组件 |
| **第二阶段：KDE 瘦身与 Baloo 清理** | **2.16 GB** | **+110 MB** | 停用 Baloo 文件索引器，关闭 KWin 毛玻璃特效，重构省电挂机链路 |
| **第三阶段：斩除搜狗输入法 OEM 版** | **2.53 GB** | **+370 MB** | 彻底剥离常驻 126MB 的搜狗输入法及其大量后台绑定服务 |
| **最终成效** | **~2.53 GB** | **+650 MB** | **大幅拓宽物理内存空间，支撑本地 Node.js / Python / 编译等重载任务** |

---

## 三、 Android Host 端精简实操

### 1. 彻底剥离 22 个冗余系统包
通过 Android 系统的 `pm uninstall -k --user 0` 机制，可以在不破坏系统分区（保留 OTA 回退能力）的前提下，实现开机 0 残留、绝不自启：

- **目标组件清单**：
  1. `com.sohu.inputmethod.sogou.oem`（搜狗输入法 OEM 版，常驻吃内存大户）
  2. `com.lenovo.ota`（系统更新后台服务）
  3. `com.lenovo.ue.device`（联想用户体验改进计划）
  4. `com.zui.xlog`（联想日志采集，频繁唤醒 CPU）
  5. `com.factory.mmigroup`（工厂测试后台）
  6. `com.android.se`（Secure Element 后台）
  7. `com.zui.net.data.monitor`（流量监控）
  8. `com.zui.networkaclr`（网络加速器）
  9. `com.android.remoteprovisioner`（远程证书）
  10. `com.qualcomm.qti.devicestatistics`（高通设备统计遥测）
  11. `com.qti.qualcomm.mstatssystem`（高通监控系统）
  12. `com.qti.diagservices`（高通诊断）
  13. `com.android.inputmethod.latin`（AOSP 备用输入法）
  14. `com.android.providers.calendar`（日历同步提供者）
  15. `com.zui.tassistent`（乐语音助手）
  16. `com.qualcomm.qtil.aptxacu`（aptX 更新器）
  17. `com.tblenovo.lenovowhatsnew`（联想推送/推广）
  18. `com.tblenovo.center`（联想会员中心/消息中心）
  19. `com.lenovo.leos.appstore`（联想应用中心后台服务）
  20. `com.zui.game.service`（游戏助手）
  21. `com.zui.udevice`（设备互联后台）
  22. `com.motorola.mobiledesktop.core`（扩展桌面残留）

- **一键执行命令**：
  ```bash
  su -c "sh /scripts/android/debloat_android.sh"
  ```
- **无损恢复命令**：
  ```bash
  su -c "sh /scripts/android/restore_android_bloat.sh"
  ```

---

## 四、 Linux 独占模式与资源保障

在 `/data/adb/kde-desktop/bin/freeze_android.sh` 中集成了完整的资源倾斜机制：

1. **cgroup 深度冻结**：将所有已识别的用户级 Android App UID 写入 `/sys/fs/cgroup/uid_<uid>/cgroup.freeze`；
2. **算力倾斜 (Core Isolation)**：
   ```bash
   echo 0-3 > /dev/cpuset/background/cpus
   echo 0-3 > /dev/cpuset/system-background/cpus
   ```
   强制将 Android 系统后台限制在前 4 个小核（CPU 0-3），将骁龙 870 强悍的中核（CPU 4-6，2.42GHz）和超大核（CPU 7，3.2GHz）全力留给 Linux 图形渲染与编译任务；
3. **OOM 内存特权保障**：
   ```bash
   for pid in $(pgrep -f "kwin_wayland|plasmashell|display_daemon|start-kde|pipewire"); do
       echo -1000 > "/proc/$pid/oom_score_adj"
   done
   ```
   锁定 Linux 关键进程为最高防御等级，确保在高负载内存紧张时 Android 的 LMK 绝不会误杀 Linux 桌面。

---

## 五、 KDE Plasma 6 桌面轻量化调优

执行 `scripts/linux/optimize_desktop.sh` 即可自动完成以下配置：

### 1. 彻底禁用 Baloo 索引器
Baloo 经常在后台默默扫描全盘文件，导致 CPU 频繁占满单核、闪存寿命受损。
```bash
balooctl6 disable
kwriteconfig6 --file baloofilerc --group 'Basic Settings' --key 'Indexing-Enabled' false
pkill -9 -f baloo
```

### 2. 关闭 KWin 沉重特效与毛玻璃
在移动端 GPU 上，实时模糊（Blur）和对比度渲染是主要的耗电与掉帧元凶。
```bash
kwriteconfig6 --file kwinrc --group Compositing --key AnimationSpeed 0
kwriteconfig6 --file kwinrc --group Plugins --key blurEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key contrastEnabled false
kwriteconfig6 --file kwinrc --group Plugins --key translucencyEnabled false
```

---

## 六、 OLED 纯黑屏省电挂机（黑屏防烧屏）

小新 Pad Pro 2021 搭载了一块 2560×1600 分辨率的高素质 90Hz OLED 屏幕。OLED 的物理特性是**纯黑像素点直接切断供电、完全不发光**。

- **实现机制**：
  - 采用 Wayland 原生 PyQt5 全屏框架（`scripts/linux/black-screen-saver.py`），全屏渲染 `#000000`；
  - 启动前 2.5 秒柔和提示操作方式，随后平滑淡出至全黑；
  - **原生手势拦截**：完美监听 `TouchBegin`、`TouchEnd` 以及鼠标和键盘事件，触控屏幕任意位置瞬间唤醒；
  - **0 常驻开销**：唤醒退出后直接终止退出，常驻内存为 0。
- **桌面快捷方式**：
  桌面预置 `templates/black-screen.desktop`，双击或单触桌面图标即可进入挂机状态。
