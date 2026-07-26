# ScriptHub Campus

ScriptHub Campus 是一个面向校园场景的 Flask 脚本分享网站，支持脚本投稿、审核、搜索、收藏、点赞、复制、下载和 AI 问答，并集成了桌宠资源包生成器。

## 主要功能

- 普通用户注册、登录和投稿管理
- 管理员与普通用户共用登录入口，按账号角色自动跳转
- 管理员审核、拒绝和删除脚本
- 脚本搜索、分类、语言筛选和分页
- 脚本详情、安全提示、点赞、收藏、复制与下载统计
- 根据语言下载 `.py`、`.ps1`、`.js`、`.sh` 等脚本文件
- DeepSeek AI 问答助手
- 桌宠工坊：使用图片或动画生成 `.petpack` 资源包

## 本地运行

建议使用 Python 3.12。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，填入自己的配置：

```env
DEEPSEEK_API_KEY=你的_DeepSeek_API_Key
FLASK_SECRET_KEY=请替换为随机长字符串
```

初始化并启动：

```powershell
python database.py
python app.py
```

打开 <http://127.0.0.1:5000>。

## 创建管理员

网站只有一个登录入口 `/login`。管理员账号登录后会自动进入审核后台。

```powershell
python create_admin.py
```

## 数据与安全

- `.env`、SQLite 数据库、虚拟环境和备份目录不会提交到 Git。
- 网站只允许下载已经审核通过的脚本。
- 运行他人上传的脚本前，请先阅读代码和详情页安全提示。
- 仓库中的桌宠播放器目前未进行商业代码签名，Windows 智能应用控制可能阻止运行。正式分发前应使用可信 RSA 代码签名证书签名。

## 部署说明

GitHub 用于托管源代码，GitHub Pages 不能直接运行 Flask 服务。公网部署需要使用支持 Python Web 服务的平台，并在平台中配置环境变量和持久化数据库。
