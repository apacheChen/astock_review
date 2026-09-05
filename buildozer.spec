[app]

# (str) Title of your application
title = astock_review

# (str) Package name
package.name = astockreview

# (str) Package domain (needed for android/ios packaging)
package.domain = org.apachechen

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the source code)
source.include_exts = py,png,jpg,kv,atlas,json,txt

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy

# (str) Application versioning (method 1)
version = 0.1

# (int) Minimum API required
android.minapi = 21

# (int) Android SDK version to use
android.api = 33

# (str) Android NDK version to use (纯版本号，严禁在行末加注释)
android.ndk = 25b

# (bool) If True, then automatically accept SDK license
android.accept_sdk_license = True

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

# (bool) Automatically keep screen on
# Keep screen on (prevents screen from going to sleep)
# android.wakelock = False

# (list) Android application permissions
# android.permissions = INTERNET

# (int) Target Android API, should be as high as possible.
# android.api = 31

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
