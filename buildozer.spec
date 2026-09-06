[buildozer]

log_level = 2
warn_on_root = 1


[app]

# ========================================
# 应用基本信息
# ========================================

title = A股复盘助手

package.name = astockreview

package.domain = org.apachechen

version = 1.0.0


# ========================================
# 项目源码
# ========================================

source.dir = .

source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,csv

source.exclude_dirs = .git,.github,.buildozer,bin,__pycache__,venv,.venv,tests,test


# ========================================
# Python 依赖
# ========================================
#
# 非常重要：
#
# python3 和 hostpython3
# 必须完全使用相同版本
#
# 上一次失败：
#
# python3 = 3.10.14
# hostpython3 = 3.14.2
#
# 导致版本冲突
#
# 这次统一锁定 Python 3.13
#
# ========================================

requirements = python3==3.13.11,hostpython3==3.13.11,kivy==2.3.0,pandas,numpy,loguru


# ========================================
# Kivy
# ========================================

orientation = portrait

fullscreen = 0


# ========================================
# Android 权限
# ========================================

android.permissions = INTERNET,ACCESS_NETWORK_STATE


# ========================================
# Android SDK
# ========================================

android.minapi = 26

android.api = 33

android.ndk_api = 26


# ========================================
# CPU 架构
# ========================================

android.archs = arm64-v8a


# ========================================
# Android 设置
# ========================================

android.accept_sdk_license = True

android.allow_backup = True


# ========================================
# Python-for-Android
# ========================================
#
# 明确使用稳定版
#
# 不使用 develop
#
# ========================================

p4a.branch = master


# ========================================
# Bootstrap
# ========================================

p4a.bootstrap = sdl2