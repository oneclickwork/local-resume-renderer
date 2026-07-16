# Local Resume Renderer

一个只在本地运行的 Markdown 简历渲染器，使用 HTML/CSS 和 Playwright 导出 PDF、PNG、JPG 与 HTML，并提供可被 Codex 调用的中文 Skill。

## 功能

- 将 Markdown 简历渲染为 A4 PDF 和图片。
- 支持联系方式图标、分节标题、粗体、列表和多列信息行。
- 支持左右对齐的公司、职位、项目名称和时间。
- 支持自动压缩到指定页数，不缩小字号、不删除内容。
- 每次生成独立的日期时间目录，同时归档输入 Markdown。
- Playwright 不可用时可回退到 Python ReportLab + Poppler。

## 安装

进入渲染器目录：

```powershell
cd plugins/local-resume-renderer
npm install
npx playwright install chromium
```

## 使用

默认从最新输出版本读取 Markdown；没有历史版本时使用 `examples/example-resume.md`：

```powershell
npm run render
```

指定输入：

```powershell
npm run render -- --input "C:\path\resume.md"
```

自动压到一页：

```powershell
npm run render -- --fit-pages 1
```

使用紧凑预设或手动参数：

```powershell
npm run render -- --compact
npm run render -- --page-margin-y 6 --line-height 1.30
```

默认输出到当前用户桌面的 `resume/<日期时间>`。可以通过环境变量修改输出根目录：

```powershell
$env:RESUME_OUTPUT_ROOT = "D:\resume-output"
npm run render
```

## Markdown 扩展语法

```markdown
::左右 **示例科技有限公司** || **2024.07-2024.12**

::: start
**示例大学**
:::
**计算机科学与技术**
:::
**2021.09-2025.06**
::: end
```

完整示例见 `plugins/local-resume-renderer/examples/example-resume.md`。

## Codex Skill

Plugin 内包含中文 `resume-renderer` Skill。通过 GitHub 发布后，可以把仓库添加为 Codex Plugin marketplace：

```powershell
codex plugin marketplace add oneclickwork/local-resume-renderer
```

重启 Codex，在插件目录中选择 `Local Resume Tools` 并安装 `local-resume-renderer`。之后可以直接说：

```text
调用 $resume-renderer，把最新简历压到一页。
```

Skill 会定位自己的 Plugin 安装目录、选择渲染参数、生成新时间版本并检查输出。

## 隐私

不要把真实简历、手机号、邮箱、微信号或生成的 PDF/图片提交到公开仓库。仓库只保留匿名示例；个人输入和输出应保存在仓库外部或被 `.gitignore` 排除。

## License

[MIT](LICENSE)
