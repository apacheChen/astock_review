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
android.ndk = 28c          # ← 改这里（原来是 r25c）
android.accept_sdk_license = True
android.allow_backup = True

# ============ 以下为新增/修改的配置（解决下载404问题） ============
# (str) python-for-android branch to use, defaults to master
p4a.branch = develop

# (str) OpenSSL version to use
openssl.version = 1.1.1w
