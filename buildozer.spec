# buildozer.spec —— Android 打包配置(# 开头为注释)

[buildozer]
log_level = 2
warn_on_root = 1

[app]
title = A股复盘助手
package.name = astockreview
package.domain = org.apachechen
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,otf
version = 1.0.0
requirements = python3,kivy==2.3.0,pandas,numpy,loguru
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.minapi = 26
android.api = 33
android.ndk_api = 26
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
