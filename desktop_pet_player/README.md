# 桌宠播放器

播放器用于导入并运行网站生成的 `.petpack` 资源包。

## v1.1

- 第一次启动会显示独立、可见的导入窗口。
- 可以选择 `.petpack`，也可以把 `.petpack` 或兼容 ZIP 拖入窗口。
- 双击系统托盘中的播放器图标即可更换桌宠。
- 导入失败后会显示具体原因，并允许重新选择。
- 下载文件包含版本号，网站响应禁止缓存旧播放器。

## 构建

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\desktop_pet_player\build-player.ps1
```

生成文件位于 `desktop_pet_player/dist/桌宠播放器.exe`。

## 自检

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\desktop_pet_player\build-player.ps1 -SelfTest
.\desktop_pet_player\dist\DesktopPetPlayerSelfTest.exe .\example.petpack
```
