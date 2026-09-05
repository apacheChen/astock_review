# buildozer.spec —— Android 打包配置(# 开头为注释)
# 作用:告诉打包工具 App 名称/依赖库/权限/支持机型

[buildozer]
log_level = 2
warn_on_root = 1

[app]
# 手机桌面上显示的名字
title = A股复盘助手

# 包名(只能小写字母数字,不能中文)
package.name = astockreview
package.domain = org.apachechen

# 源码目录=仓库根目录,main.py 和整个 src/ 都会打进安装包
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,otf

# 版本号
version = 1.0.0

# 随包安装的 Python 库(pandas/numpy/kivy 有官方预编译支持)
requirements = python3,kivy==2.3.0,pandas,numpy,loguru

# 竖屏、不全屏
orientation = portrait
fullscreen = 0

# 权限:联网 + 检查网络状态(拉行情数据必须)
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# 支持范围:Android 8.0 及以上,覆盖近 8 年几乎所有手机
android.minapi = 26
android.api = 34
android.ndk_api = 26
android.archs = arm64-v8a

# 构建时自动接受 SDK 许可,免交互卡住
android.accept_sdk_license = True
android.allow_backup = True
