# 回退与常见问题

- **安装拒绝覆盖**：属于预期保护。不要改脚本跳过；先备份并采用独立的迁移方案。
- **回到 Android**：Android Home 或在 Linux 写宿主命令 `switch-to-android`。
  停止开机自启用 `set-autostart.sh off`，或者将 `/data/adb/boot_mode` 设置为 `android_always`。
- **KDE 不启动**：查看 `/data/adb/kde-desktop/logs/start-kde.log`，确认配套 daemon、
  客户端、设备节点、SELinux选择和 `/run/display.sock`。
- **音频或相机无数据**：先确认客户端位于前台、权限已授予，再检查 PipeWire。
  麦克风应在录音期间开启、结束后停止，不通过隐藏 Android 指示器掩盖实际采集。
- **软件更新覆盖定制组件**：KWin、Mesa、Xwayland 等保持版本冻结。
  不建议无计划取消冻结；升级需准备对应补丁和回滚并重新测试。
- **sudo/FUSE 不工作**：Android `/data` 为 nosuid，确认 tmpfs 特权工具钩子工作。
  不在 chroot 中为消除报错启动 system D-Bus。
- **终端任务**：任务保留依赖从持久 Konsole 配置创建的 tmux 会话。
  不要用 `pkill -u 1000`；Android 系统同样使用 UID1000，必须按 chroot 和进程身份区分。
- **卸载**：先返回 Android、关闭开机自启、停止桌面并备份自己的 Linux 数据。
  本预览不提供一键递归删除运行 rootfs 的脚本，避免误删挂载的 Android 或 SD 卡数据。
- **反馈日志**：发送前删除 URL 参数、账号、文件路径和代理凭据，不整包上传家目录。
