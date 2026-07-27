import json
from datetime import datetime


CURATED_SCRIPTS = [
    {
        "title": "查找适用于当前网站的脚本",
        "author_name": "Pipe Craft",
        "description": (
            "在当前网页一键查询 Greasy Fork、ScriptCat、GitHub "
            "等脚本仓库，适合发现与当前网站匹配的油猴脚本。"
        ),
        "language": "JavaScript",
        "category": "脚本管理",
        "tags": ["油猴", "脚本发现", "多平台", "效率"],
        "license_name": "MIT",
        "original_version": "0.4.3",
        "source_updated_at": "2026-03-17",
        "source_url": (
            "https://greasyfork.org/zh-CN/scripts/"
            "550659-find-scripts-for-this-site"
        ),
        "install_url": (
            "https://update.greasyfork.org/scripts/550659/"
            "Find%20Scripts%20For%20This%20Site.user.js"
        ),
        "warnings": [
            "会访问多个第三方脚本仓库来搜索脚本。",
            "搜索结果中的其他脚本仍需单独检查权限和代码。"
        ]
    },
    {
        "title": "极简划词搜索",
        "author_name": "ddr win",
        "description": (
            "选中文字后快速复制、打开链接或使用多个搜索引擎搜索，"
            "同时支持拖拽链接和图片。"
        ),
        "language": "JavaScript",
        "category": "搜索效率",
        "tags": ["划词", "搜索", "高亮", "效率"],
        "license_name": "MIT",
        "original_version": "2.5.2",
        "source_updated_at": "2026-05-19",
        "source_url": (
            "https://greasyfork.org/zh-CN/scripts/"
            "566626-%E6%9E%81%E7%AE%80%E5%88%92%E8%AF%8D%E6%90%9C%E7%B4%A2"
        ),
        "install_url": (
            "https://update.greasyfork.org/scripts/566626/"
            "%E6%9E%81%E7%AE%80%E5%88%92%E8%AF%8D%E6%90%9C%E7%B4%A2.user.js"
        ),
        "warnings": [
            "搜索操作会把选中的文字发送给所选择的搜索引擎。",
            "拖拽图片下载可能受目标网站的跨域限制影响。"
        ]
    },
    {
        "title": "网页限制解除",
        "author_name": "Cat73",
        "description": (
            "恢复网页上的文字选择、复制、剪切和右键菜单，"
            "适合阅读资料与整理公开信息。"
        ),
        "language": "JavaScript",
        "category": "网页增强",
        "tags": ["复制", "右键", "文本选择", "网页增强"],
        "license_name": "LGPL-3.0",
        "original_version": "1.3",
        "source_updated_at": "2022-01-09",
        "source_url": (
            "https://greasyfork.org/zh-CN/scripts/"
            "14146-%E7%BD%91%E9%A1%B5%E9%99%90%E5%88%B6%E8%A7%A3%E9%99%A4"
        ),
        "install_url": (
            "https://update.greasyfork.org/scripts/14146/"
            "%E7%BD%91%E9%A1%B5%E9%99%90%E5%88%B6%E8%A7%A3%E9%99%A4.user.js"
        ),
        "warnings": [
            "会修改网页的鼠标和键盘事件处理。",
            "少数网站功能可能受影响，可在脚本管理器中对该网站停用。"
        ]
    },
    {
        "title": "护眼模式",
        "author_name": "X.I.U",
        "description": (
            "为大多数网页提供亮度降低、暖色调和深色显示模式，"
            "适合夜间阅读和长时间浏览。"
        ),
        "language": "JavaScript",
        "category": "阅读体验",
        "tags": ["护眼", "深色模式", "夜间", "全站"],
        "license_name": "GPL-3.0",
        "original_version": "1.5.8",
        "source_updated_at": "2026-04-22",
        "source_url": (
            "https://greasyfork.org/zh-CN/scripts/426377-dark-mode"
        ),
        "install_url": (
            "https://update.greasyfork.org/scripts/426377/"
            "%E6%8A%A4%E7%9C%BC%E6%A8%A1%E5%BC%8F.user.js"
        ),
        "warnings": [
            "会使用 CSS 滤镜改变网页显示效果。",
            "某些网页或 Firefox 中可能出现颜色、图片或悬浮元素异常。"
        ]
    },
    {
        "title": "链接助手",
        "author_name": "Pipe Craft",
        "description": (
            "将文本、Markdown 和 BBCode 链接转换为可点击链接，"
            "并支持按规则在新标签页打开站内或站外链接。"
        ),
        "language": "JavaScript",
        "category": "网页增强",
        "tags": ["链接", "新标签页", "文本识别", "网页增强"],
        "license_name": "MIT",
        "original_version": "0.14.3",
        "source_updated_at": "2026-04-15",
        "source_url": (
            "https://greasyfork.org/zh-CN/scripts/464541-links-helper"
        ),
        "install_url": (
            "https://update.greasyfork.org/scripts/464541/"
            "%F0%9F%94%97%20Links%20Helper.user.js"
        ),
        "warnings": [
            "会读取和修改网页中的链接元素。",
            "图片代理是可选功能，启用后图片请求可能经过第三方服务。"
        ]
    }
]


def seed_curated_scripts(conn):
    """把经过筛选的第三方脚本作为可追溯目录条目写入数据库。"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for script in CURATED_SCRIPTS:
        conn.execute("""
            INSERT INTO scripts (
                user_id,
                author_name,
                title,
                description,
                language,
                category,
                tags,
                code,
                status,
                review_note,
                line_count,
                non_empty_line_count,
                warnings,
                created_at,
                updated_at,
                reviewed_at,
                source_name,
                source_url,
                install_url,
                license_name,
                original_version,
                source_updated_at,
                is_curated
            )
            VALUES (
                NULL, ?, ?, ?, ?, ?, ?, '',
                'approved', ?, 0, 0, ?, ?, ?, ?,
                'Greasy Fork', ?, ?, ?, ?, ?, 1
            )
            ON CONFLICT DO NOTHING
        """, (
            script["author_name"],
            script["title"],
            script["description"],
            script["language"],
            script["category"],
            json.dumps(
                script["tags"],
                ensure_ascii=False
            ),
            "第三方精选脚本，安装文件由 Greasy Fork 官方提供。",
            json.dumps(
                script["warnings"],
                ensure_ascii=False
            ),
            current_time,
            current_time,
            current_time,
            script["source_url"],
            script["install_url"],
            script["license_name"],
            script["original_version"],
            script["source_updated_at"]
        ))
