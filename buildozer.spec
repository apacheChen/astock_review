# buildozer.spec —— Android 打包配置（# 开头为注释）

[buildozer]
log_level = 2
warn_on_root = 1

[app]
title = A股复盘助手
package.name = astockreview
package.domain = org.apachechen
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
requirements = python3,kivy==2.3.0,pandas,numpy,loguru
version = 1.0.0
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.minapi = 26
android.api = 33
android.ndk_api = 26
android.archs = arm64-v8a
android.ndk = 28c
android.accept_sdk_license = True
android.allow_backup = True

# ===== 以下为修复下载 404 的必要配置（请务必保留） =====
p4a.branch = develop
openssl.version = 1.1.1w
