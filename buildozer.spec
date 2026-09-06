[buildozer]

# 构建日志级别
log_level = 2

# GitHub Actions 中无需 root 警告
warn_on_root = 1


[app]

# =========================
# 应用基本信息
# =========================

# 应用显示名称
title = A股复盘助手

# Android 包名
package.name = astockreview

# 包域名
package.domain = org.apachechen

# 应用版本
version = 1.0.0


# =========================
# 项目源码
# =========================

# 当前项目根目录
source.dir = .

# 允许打包的文件扩展名
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,csv

# 排除不需要打包的目录
source.exclude_dirs = .git,.github,.buildozer,bin,__pycache__,venv,.venv,tests,test


# =========================
# Python 依赖
# =========================

# 注意：
# 不锁死 python3 的小版本
# 由 python-for-android 自动选择兼容版本
requirements = python3,kivy==2.3.0,pandas,numpy,loguru


# =========================
# Kivy / Android
# =========================

# 屏幕方向
orientation = portrait

# 是否全屏
fullscreen = 0


# =========================
# Android 权限
# =========================

android.permissions = INTERNET,ACCESS_NETWORK_STATE


# =========================
# Android SDK
# =========================

# 最低 Android API
android.minapi = 26

# 编译 API
android.api = 33

# NDK API
android.ndk_api = 26


# =========================
# CPU 架构
# =========================

# 现代 Android 手机主要使用 ARM64
android.archs = arm64-v8a


# =========================
# Android 构建设置
# =========================

android.accept_sdk_license = True

android.allow_backup = True


# =========================
# 禁止使用开发版 p4a
# =========================

# 不设置：
# p4a.branch = develop
#
# 让 Buildozer 使用自身兼容的 python-for-android


# =========================
# 调试
# =========================

# 保持默认 SDL2 Bootstrap
# 不需要手动设置 bootstrap
