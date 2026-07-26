def analyze_code(code):
    """分析用户提交的代码，并返回结构化结果。"""
    language_rules = {
        "Python": ["def ", "import ", "from ", "print(", "__name__"],
        "JavaScript": ["const ", "let ", "function ", "console.log", "=>"],
        "PowerShell": [
            "get-childitem",
            "write-host",
            "remove-item",
            "$_",
            "param("
        ],
        "Bash": [
            "#!/bin/bash",
            "#!/usr/bin/env bash",
            "echo ",
            "sudo ",
            "chmod "
        ]
    }

    risk_rules = {
        "代码可能会删除文件。": [
            "os.remove",
            "shutil.rmtree",
            "remove-item",
            "rm -rf",
            "unlink("
        ],
        "代码可能会执行系统命令。": [
            "os.system",
            "subprocess",
            "shell=true",
            "invoke-expression"
        ],
        "代码可能会访问网络。": [
            "requests.get",
            "requests.post",
            "fetch(",
            "invoke-webrequest",
            "curl "
        ]
    }

    cleaned_code = code.strip()

    if not cleaned_code:
        return {
            "success": False,
            "error": "代码不能为空。"
        }

    lines = cleaned_code.splitlines()
    non_empty_lines = []

    for line in lines:
        if line.strip():
            non_empty_lines.append(line)

    lower_code = cleaned_code.lower()
    language_scores = {}

    for language, keywords in language_rules.items():
        score = 0

        for keyword in keywords:
            if keyword.lower() in lower_code:
                score += 1

        language_scores[language] = score

    detected_language = max(
        language_scores,
        key=language_scores.get
    )

    if language_scores[detected_language] == 0:
        detected_language = "Unknown"

    warnings = []

    for warning_message, keywords in risk_rules.items():
        for keyword in keywords:
            if keyword.lower() in lower_code:
                warnings.append(warning_message)
                break

    preview_parts = []

    for line in non_empty_lines:
        preview_parts.append(line.strip())

    preview = " ".join(preview_parts)

    if len(preview) > 100:
        preview = preview[:100] + "..."

    return {
        "success": True,
        "language": detected_language,
        "language_scores": language_scores,
        "line_count": len(lines),
        "non_empty_line_count": len(non_empty_lines),
        "warnings": warnings,
        "preview": preview
    }
