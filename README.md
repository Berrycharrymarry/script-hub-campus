# ScriptHub Campus

ScriptHub Campus 是一个面向校园场景的 Flask 脚本分享网站，支持脚本投稿、审核、搜索、收藏、点赞、复制、下载和 AI 问答，并集成了桌宠资源包生成器。

## 主要功能

- 普通用户注册、登录和投稿管理
- 管理员与普通用户共用登录入口，按账号角色自动跳转
- 管理员审核、拒绝和删除脚本
- 脚本搜索、分类、语言与标签筛选和分页
- 脚本详情、安全提示、点赞、收藏、复制与下载统计
- 根据语言下载 `.py`、`.ps1`、`.js`、`.sh` 等脚本文件
- Greasy Fork 精选目录：展示原作者、来源、许可证、原版版本与更新时间
- 第三方精选脚本通过 Greasy Fork 官方安装地址获取，避免分发过期镜像
- DeepSeek AI 问答助手
- 桌宠工坊：使用图片或动画生成 `.petpack` 资源包
- Neon Rail Runner（Metro Rush 3D）Unity WebGL 浏览器游戏

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
DATABASE_URL=
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
- 精选第三方脚本保留原作者、原始页面和开源许可证信息。
- 第三方脚本的安装文件由 `update.greasyfork.org` 官方源提供；安装前仍应检查权限、代码和用户反馈。
- 运行他人上传的脚本前，请先阅读代码和详情页安全提示。
- 仓库中的桌宠播放器目前未进行商业代码签名，Windows 智能应用控制可能阻止运行。正式分发前应使用可信 RSA 代码签名证书签名。

## 部署说明

GitHub 用于托管源代码，GitHub Pages 不能直接运行 Flask 服务。公网部署需要使用支持 Python Web 服务的平台，并在平台中配置环境变量和持久化数据库。

仓库包含 `render.yaml`，可直接在 Render 中创建 Blueprint：

- Render 自动安装依赖并使用 Gunicorn 启动 Flask。
- `FLASK_SECRET_KEY` 由 Render 自动生成。
- `DATABASE_URL` 在 Render 中作为私密环境变量保存；配置后线上使用 PostgreSQL，本地留空时仍使用 SQLite。
- `DEEPSEEK_API_KEY` 需要在创建服务时作为私密环境变量填写。
- `ADMIN_USERNAME` 与 `ADMIN_PASSWORD_HASH` 必须成对配置；服务器启动时会自动创建或恢复该管理员账号，密码哈希不会提交到 GitHub。
- PostgreSQL 中的用户、投稿、评论、点赞和收藏不会因 Render 休眠、重启或重新部署而丢失。
