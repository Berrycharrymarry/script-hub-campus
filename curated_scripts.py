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
    },
    {
        "title": "HTML5 视频播放工具",
        "author_name": "xinggsf",
        "description": (
            "为主流 HTML5 视频网站增加播放速度、快进快退、"
            "画中画、截图、全屏和音量等键盘快捷控制。"
        ),
        "language": "JavaScript",
        "category": "视频工具",
        "tags": [
            "Userscript.Zone",
            "视频控制",
            "快捷键",
            "画中画",
            "播放速度",
            "效率"
        ],
        "discovery_source": "Userscript.Zone",
        "discovery_url": (
            "https://www.userscript.zone/search"
            "?l=zh-CN&q=youtube&start=0"
        ),
        "source_name": "Greasy Fork",
        "license_name": "MIT",
        "original_version": "2.0.2",
        "source_updated_at": "2025-08-06",
        "source_url": (
            "https://greasyfork.org/zh-CN/scripts/30545"
        ),
        "install_url": (
            "https://update.greasyfork.org/scripts/30545/"
            "script.user.js"
        ),
        "warnings": [
            "脚本会在多个视频网站监听键盘操作，可能与网站原有快捷键冲突。",
            "截图、缓存和画中画功能会受到浏览器及目标网站限制。"
        ]
    },
    {
        "title": "YouTube JS Engine Tamer",
        "author_name": "CY Fung",
        "description": (
            "调整 YouTube 页面内部渲染与事件机制，"
            "用于减少重复处理、内存占用和界面卡顿。"
        ),
        "language": "JavaScript",
        "category": "性能优化",
        "tags": [
            "Userscript.Zone",
            "YouTube",
            "性能优化",
            "内存",
            "实验性",
            "视频"
        ],
        "discovery_source": "Userscript.Zone",
        "discovery_url": (
            "https://www.userscript.zone/search"
            "?l=zh-CN&q=youtube&start=0"
        ),
        "source_name": "Greasy Fork",
        "license_name": "MIT",
        "original_version": "0.42.25",
        "source_updated_at": "2026-07-25",
        "source_url": (
            "https://greasyfork.org/zh-CN/scripts/"
            "473972-youtube-js-engine-tamer"
        ),
        "install_url": (
            "https://update.greasyfork.org/scripts/473972/"
            "script.user.js"
        ),
        "warnings": [
            "这是实验性脚本，会修改 YouTube 的内部 JavaScript 运行机制。",
            "YouTube 更新后可能出现界面或播放异常，遇到问题应先停用脚本。"
        ]
    },
    {
        "title": "Reddit++",
        "author_name": "lnm95",
        "description": (
            "为新版 Reddit 提供关键词过滤、图片缩放、"
            "字体调整、侧栏整理、书签和评论阅读增强。"
        ),
        "language": "JavaScript",
        "category": "社区增强",
        "tags": [
            "Userscript.Zone",
            "Reddit",
            "关键词过滤",
            "阅读体验",
            "界面优化",
            "书签"
        ],
        "discovery_source": "Userscript.Zone",
        "discovery_url": (
            "https://www.userscript.zone/search"
            "?l=en&q=reddit&start=0"
        ),
        "source_name": "Greasy Fork",
        "license_name": "MIT",
        "original_version": "2.1.6",
        "source_updated_at": "2026-06-20",
        "source_url": (
            "https://greasyfork.org/zh-CN/scripts/490046-reddit"
        ),
        "install_url": (
            "https://update.greasyfork.org/scripts/490046/"
            "script.user.js"
        ),
        "warnings": [
            "只支持新版 Reddit，旧版界面和移动端不在作者支持范围内。",
            "会在浏览器本地保存过滤词、书签和界面设置。"
        ]
    },
    {
        "title": "脚本查找大师（四大脚本库合一显数版）",
        "author_name": "白鸽男孩（bimzcy）",
        "description": (
            "聚合查询 Greasy Fork、Sleazy Fork、ScriptCat "
            "和 GitHub Gist，并在当前网页显示可用脚本数量。"
        ),
        "language": "JavaScript",
        "category": "脚本管理",
        "tags": [
            "ScriptCat",
            "脚本发现",
            "聚合搜索",
            "Greasy Fork",
            "GitHub Gist",
            "效率"
        ],
        "discovery_source": "ScriptCat",
        "discovery_url": (
            "https://scriptcat.org/zh-CN/script-show-page/6940"
        ),
        "source_name": "ScriptCat",
        "license_name": "Zlib/Libpng",
        "original_version": "7.6",
        "source_updated_at": "2026-07-16",
        "source_url": (
            "https://scriptcat.org/zh-CN/script-show-page/6940"
        ),
        "install_url": (
            "https://scriptcat.org/scripts/code/6940/"
            "%E8%84%9A%E6%9C%AC%E6%9F%A5%E6%89%BE%E5%A4%A7"
            "%E5%B8%88%EF%BC%88%E5%9B%9B%E5%A4%A7%E8%84%9A"
            "%E6%9C%AC%E5%BA%93%E5%90%88%E4%B8%80%E6%98%BE"
            "%E6%95%B0%E7%89%88%EF%BC%89.user.js"
        ),
        "warnings": [
            "会在所有网页运行，并向四个第三方脚本仓库查询当前网站。",
            "搜索结果中的脚本仍需逐个检查作者、权限、许可证和用户反馈。"
        ]
    },
    {
        "title": "豆瓣观影记录一键复制",
        "author_name": "JSSM（bvagwrvgarb）",
        "description": (
            "在豆瓣“我看过的影视”页面增加复制按钮，"
            "导出片名、年份、评分、日期和短评，便于整理分析。"
        ),
        "language": "JavaScript",
        "category": "资料整理",
        "tags": [
            "ScriptCat",
            "豆瓣电影",
            "数据导出",
            "复制增强",
            "观影记录",
            "效率"
        ],
        "discovery_source": "ScriptCat",
        "discovery_url": (
            "https://scriptcat.org/zh-CN/script-show-page/5938"
        ),
        "source_name": "ScriptCat",
        "license_name": "MIT",
        "original_version": "0.9",
        "source_updated_at": "2026-06-22",
        "source_url": (
            "https://scriptcat.org/zh-CN/script-show-page/5938"
        ),
        "install_url": (
            "https://scriptcat.org/scripts/code/5938/"
            "%E8%B1%86%E7%93%A3%E8%A7%82%E5%BD%B1%E8%AE%B0"
            "%E5%BD%95%E4%B8%80%E9%94%AE%E5%A4%8D%E5%88%B6"
            ".user.js"
        ),
        "warnings": [
            "只在豆瓣个人观影记录页面运行。",
            "复制结果可能包含你写下的私人短评，粘贴或分享前应检查内容。"
        ]
    },
    {
        "title": "GitHub 增强：高速下载",
        "author_name": "X.I.U（ScriptCat: Jeremy）",
        "description": (
            "为 GitHub 的 Clone、Release、Raw 和 ZIP 文件增加"
            "公益镜像下载入口，并支持仓库列表单文件下载。"
        ),
        "language": "JavaScript",
        "category": "开发工具",
        "tags": [
            "ScriptCat",
            "GitHub",
            "下载辅助",
            "开发工具",
            "镜像",
            "开源"
        ],
        "discovery_source": "ScriptCat",
        "discovery_url": (
            "https://scriptcat.org/zh-CN/script-show-page/900"
        ),
        "source_name": "ScriptCat",
        "license_name": "GPL-3.0",
        "original_version": "2.6.38",
        "source_updated_at": "2026-05-28",
        "source_url": (
            "https://scriptcat.org/zh-CN/script-show-page/900"
        ),
        "install_url": (
            "https://scriptcat.org/scripts/code/900/"
            "Github%20Enhancement%20-%20High%20Speed%20Download"
            ".user.js"
        ),
        "warnings": [
            "高速下载链接可能经过第三方公益镜像或代理服务。",
            "下载敏感项目、发布包或可执行文件时应核对来源与校验值。"
        ]
    },
    {
        "title": "抖音优化",
        "author_name": "WhiteSevs（whitesev）",
        "description": (
            "优化抖音网页版的视频过滤、登录弹窗、自动播放、"
            "画质、全屏、弹幕、礼物特效和界面样式。"
        ),
        "language": "JavaScript",
        "category": "视频体验",
        "tags": [
            "ScriptCat",
            "抖音",
            "视频过滤",
            "界面优化",
            "播放器增强",
            "广告过滤"
        ],
        "discovery_source": "ScriptCat",
        "discovery_url": (
            "https://scriptcat.org/zh-CN/script-show-page/2534"
        ),
        "source_name": "ScriptCat",
        "license_name": "GPL-3.0-only",
        "original_version": "2026.7.26",
        "source_updated_at": "2026-07-26",
        "source_url": (
            "https://scriptcat.org/zh-CN/script-show-page/2534"
        ),
        "install_url": (
            "https://scriptcat.org/scripts/code/2534/"
            "%E6%8A%96%E9%9F%B3%E4%BC%98%E5%8C%96.user.js"
        ),
        "warnings": [
            "脚本申请存储、下载、跨域请求等权限，并会加载外部开源依赖。",
            "不要使用来源不明的自定义过滤函数；这类函数可能发送页面数据。"
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
                discovery_source,
                discovery_url,
                install_url,
                license_name,
                original_version,
                source_updated_at,
                is_curated
            )
            VALUES (
                NULL, ?, ?, ?, ?, ?, ?, '',
                'approved', ?, 0, 0, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, 1
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
            (
                "第三方精选脚本，安装文件由来源站或"
                "原始脚本托管站官方提供。"
            ),
            json.dumps(
                script["warnings"],
                ensure_ascii=False
            ),
            current_time,
            current_time,
            current_time,
            script.get(
                "source_name",
                "Greasy Fork"
            ),
            script["source_url"],
            script.get(
                "discovery_source",
                script.get(
                    "source_name",
                    "Greasy Fork"
                )
            ),
            script.get(
                "discovery_url",
                script["source_url"]
            ),
            script["install_url"],
            script["license_name"],
            script["original_version"],
            script["source_updated_at"]
        ))
