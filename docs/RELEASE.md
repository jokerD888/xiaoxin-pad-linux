# 发布与版本范围

## 发布源码

项目已初始化本地 Git 仓库，未绑定 GitHub remote，也未生成包含维护者身份的提交。
使用你自己的 GitHub 账号和提交身份：

```sh
git add .
git diff --cached --stat
git commit -m "Initial preview"
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

`dist/` 和 `.build/` 不会被 `git add .` 加入。不要用 `git add -f` 把这些目录塞进仓库。
发布附件以 `dist/UPLOAD_LIST.txt` 为准，不要上传构建中间件或整个私有工作目录。

## 发布附件

- 干净的 `xiaoxin-rootfs-0.1.0-preview.tar.xz`。
- Android 接入脚本包和 `anland-daemon-0.1.0-preview.zip`。
- 重新编译、发行签名的 `anland-linux-0.1.0-preview.apk`。
- 对应的 Anland/KWin 源码补丁、源代码与构建说明附件。
- `SHA256SUMS`，软件清单及脱敏检查报告。

GitHub Release 单个附件目前需小于 2 GiB；超限时须分卷与校验，
不能把缺少某一分卷的镜像标记为完整文件。
[GitHub 官方说明](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

## 验证边界

母版实机验证了图形、音视频、键盘、触控板、终端持久任务及空闲性能修复。
干净镜像验证了包数据库、关键运行库、账号/权限、模板、路径与隐私条件。
母版的数据与 Android 应用授权不等于新设备已完成安装。

本版还需要在全新安装上验证：解压安装、首次密码与身份初始化、冷启动、
Android 授权、KDE启动、录像录音、桌面/终端切换、重启及退出恢复。
不要用修改日期或压缩成功代替这些验收。

## 第三方许可和对应源码

Anland 为 GPLv3；本项目的原有许可证标识和第三方版权继续保留。
源码附件、补丁、基线提交和构建方法与二进制一起提供。
KWin 使用 Anland 源树内对应后端；镜像仍包含其他第三方软件。
`manifests/packages.json` 记录其许可证与上游 URL，镜像保留 `/usr/share/licenses`。
维护者还须保证 GPL 等组件的对应源码获取满足其许可，
许可证清单或指向上游主页的 URL 本身不等于所有组件的源码交付已完成。
本版没有冒充完成全镜像的逐包法律审核。

Chrome、Widevine 与 AGY 二进制不在基础镜像内，使用者从其允许的渠道另行安装。
不镜像 vendor 系统库、固件、ROM 或维护者的账号数据。

发行签名不同于母版调试签名。现有同包名调试客户端不能直接覆盖安装正式签名版。
保留发行私钥用于今后的同签名更新；私钥和密码不进入 Git、Release 或 rootfs。
