---
name: resume-renderer
description: 使用本地 Markdown 简历渲染器导出 PDF、PNG、JPG 和 HTML。用于渲染、导出、重新生成或压缩简历页数，尤其是用户提到简历渲染、Markdown 简历、PDF 简历、图片简历、压到一页、减少空白、紧凑简历风格或 resume renderer 时。
---

# 简历渲染器

## 定位项目

根据当前 `SKILL.md` 的实际路径定位 Plugin 根目录。该文件位于：

```text
<plugin-root>/skills/resume-renderer/SKILL.md
```

因此 Plugin 根目录是 Skill 目录向上两级。始终使用解析后的绝对路径运行命令，不要写死盘符、用户名或安装目录。

## 准备依赖

如果 `<plugin-root>/node_modules/playwright` 不存在，运行：

```powershell
npm --prefix "<plugin-root>" install
npm --prefix "<plugin-root>" exec playwright install chromium
```

Chromium 不可用时，渲染器会尝试回退到 Python ReportLab + Poppler。

## 选择输入

- 用户指定 Markdown 时，传入 `--input "<absolute-markdown-path>"`。
- 用户未指定时，不传 `--input`。渲染器会优先读取输出根目录下最新时间版本中的 Markdown，其次读取 Plugin 根目录或 `examples` 中的 Markdown。
- 每次渲染都把实际输入 Markdown 复制到新版本目录，禁止覆盖历史版本。

## 选择版式

- 普通渲染：不添加版式参数。
- 用户要求更紧凑：添加 `--compact`。
- 用户要求压到一页或指定页数：优先添加 `--fit-pages <页数>`。
- 用户指定参数：使用 `--page-margin-y <毫米>` 和 `--line-height <比例>`。
- 自动适配保持字号不变，只调整上下边距、行高和段落间距。显示 `target not met` 时，不要擅自删除文字。

示例：

```powershell
npm --prefix "<plugin-root>" run render
npm --prefix "<plugin-root>" run render -- --fit-pages 1
npm --prefix "<plugin-root>" run render -- --input "C:\path\resume.md" --compact
npm --prefix "<plugin-root>" run render -- --page-margin-y 6 --line-height 1.30
```

## 输出规则

- 默认输出根目录为当前用户桌面的 `resume` 文件夹。
- 设置 `RESUME_OUTPUT_ROOT` 可以覆盖默认输出根目录。
- 每次创建 `YYYY-MM-DD_HH-mm-ss` 子目录，保存输入 Markdown、`resume.html`、`resume.pdf`、`resume.png` 和 `resume.jpg`。

## 验证

1. 确认五类文件均已生成且大小非零。
2. 使用 PDF 工具确认页数；使用图片查看工具检查重叠、截断、异常空白和中文乱码。
3. 自动适配时确认命令输出包含正确的 `pages` 和 `target met`。
4. 最终回复提供本次时间版本目录及主要输出文件的绝对路径。
