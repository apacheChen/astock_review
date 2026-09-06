# buildozer.spec —— Android 打包配置

[buildozer]
log_level = 2
warn_on_root = 1

[app]
title = A股复盘助手
package.name = astockreview
package.domain = org.apachechen
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt
requirements = python3==3.10.14,kivy==2.3.0,pandas==2.0.3,numpy==1.24.4,loguru
version = 1.0.0
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.minapi = 26
android.api = 33
android.ndk_api = 26
android.archs = arm64-v8a
android.ndk = 25b
android.accept_sdk_license = True
android.allow_backup = True

# 使用 master 分支，避免自动覆盖 NDK 版本
p4a.branch = master
openssl.version = 1.1.1w
