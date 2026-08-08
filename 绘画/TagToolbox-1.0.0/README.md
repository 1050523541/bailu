# TagToolbox

词库工具箱**桌面程序**（自带窗口，不依赖外部浏览器页面）。

## 版本

版本号写在根目录 `VERSION`（当前打包产物形如 `dist\TagToolbox-1.0.0\TagToolbox-1.0.0.exe`）。改版本只需改该文件后重新打包。

## 使用

1. 打开 `dist\TagToolbox-<版本>\`
2. 双击 `TagToolbox-<版本>.exe`
3. 程序窗口内直接使用词库组合 / 分类编辑 / 提示词预设管理
4. 关闭窗口即退出

分发时拷贝整个 `dist\TagToolbox-<版本>\` 文件夹。

## 重新打包

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_app.ps1
```

## 开发运行

```powershell
python -X utf8 .\launcher.py
```

技术结构：本地 API 服务在进程内运行；界面用系统 WebView2 嵌在程序窗口里，不再打开 Chrome/Edge 浏览器标签页。
