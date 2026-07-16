# Local Resume Renderer

[简体中文](README.md) | **English**

> **A pure Vibe Coding product**

A high-aesthetic, black-and-white local Markdown resume renderer. Instead of relying on decorative colors and visual widgets, it creates hierarchy through typography, whitespace, rules, bold text, and precise alignment. The result is designed for screen reading, monochrome printing, and professional applications.

The project uses HTML/CSS and Playwright to export PDF, PNG, JPG, and HTML, and includes a reusable Skill for Codex and Claude Code.

## Copy This Prompt to Install with AI

You do not need to follow the installation guide step by step. Copy the complete prompt below into **Codex, Claude Code, or another AI coding tool with terminal and file access**:

```text
Install, configure, and verify this local resume renderer for me:
https://github.com/oneclickwork/local-resume-renderer

Execute the work whenever possible instead of only repeating the README.

1. Detect the operating system, current environment, and whether you are Codex, Claude Code, or another AI coding tool.
2. If you are Codex:
   - Prefer running: codex plugin marketplace add oneclickwork/local-resume-renderer
   - If this Codex version can manage marketplaces but cannot install a plugin non-interactively, do not stop and ask me to finish it manually. Clone the repository into a stable local tools directory, then install plugins/local-resume-renderer/skills/resume-renderer into the user-level Skills directory recognized by this Codex version using a symlink or directory junction.
3. If you are Claude Code:
   - Run: claude plugin marketplace add oneclickwork/local-resume-renderer
   - Run: claude plugin install local-resume-renderer@local-resume-tools --scope user
   - Reload plugins after installation. If the current session cannot reload them, clearly tell me that a new session is required.
4. For another AI coding tool, clone the repository and create the persistent Skill, Command, or rules entry supported by that tool. Do not change the renderer's core behavior.
5. Locate the actual plugin root, run npm install, and install Playwright Chromium. Never commit node_modules.
6. Run a --fit-pages 1 test with examples/example-resume.md.
7. Confirm that PDF, PNG, JPG, HTML, and a Markdown input snapshot were generated. Verify the PDF page count and inspect the image layout.
8. Do not read, upload, or commit private resumes from this machine. Use only the anonymous repository example for installation tests.
9. Report the installation location, invocation name, test output directory, and update procedure.

After installation, immediately invoke the resume rendering capability and complete the anonymous example test.
```

## The Easiest Way to Use It

After installation, attach your existing resume to the AI conversation or replace the path placeholder below. The AI will read the anonymous template, place your real content into the same structure, and render the result:

The user only needs to provide the **existing resume, target role, and target page count**. There is no need to learn the Markdown extensions or edit CSS manually. If the target role is not decided yet, omit it and let the AI preserve the source resume faithfully.

```text
Use the installed resume-renderer capability.

My current resume: <enter a file path, or read the resume attached to this conversation>
Target role: <enter the target role>
Target page count: 1

Requirements:
1. Locate and read examples/example-resume.md from the resume renderer. Learn its structure, layout syntax, and content organization.
2. Read my current resume and extract education, employment or internships, projects, technical skills, and measurable outcomes.
3. Create a new Markdown resume using the template structure. You may improve wording and ordering, but never invent companies, projects, technologies, dates, or metrics.
4. Keep my original resume unchanged and save the new Markdown as a separate file.
5. Use concise and professional language appropriate for technical roles. Project descriptions should emphasize responsibilities, approach, technology, and outcomes.
6. Render PDF, PNG, JPG, and HTML, and archive the input Markdown in a new timestamped directory.
7. Prefer --fit-pages 1. If the resume still cannot safely fit on one page, do not remove important experience without telling me.
8. Verify PDF page count, fonts, left-right alignment, pagination, bottom whitespace, overlap, and clipping.
9. Return accessible paths to every output and briefly summarize the content improvements.
```

## Preview

![Black-and-white technical resume preview](docs/demo.png)

> The preview uses anonymous sample data. Its complete source is available at `plugins/local-resume-renderer/examples/example-resume.md`.

## Features

- Render Markdown resumes as A4 PDF and images.
- Support contact icons, section headings, bold text, lists, and multi-column information rows.
- Align companies, roles, project names, and dates to opposite sides.
- Automatically fit a target page count without reducing font size or deleting content.
- Create a separate timestamped directory for every run and archive the input Markdown.
- Fall back to Python ReportLab and Poppler when Playwright is unavailable.

## Installation

```powershell
cd plugins/local-resume-renderer
npm install
npx playwright install chromium
```

## Usage

Render the latest Markdown input, or use `examples/example-resume.md` when no previous output exists:

```powershell
npm run render
```

Specify an input:

```powershell
npm run render -- --input "C:\path\resume.md"
```

Fit one page automatically:

```powershell
npm run render -- --fit-pages 1
```

Use a compact preset or manual spacing:

```powershell
npm run render -- --compact
npm run render -- --page-margin-y 6 --line-height 1.30
```

Outputs are written to `Desktop/resume/<timestamp>` by default. Override the root directory with:

```powershell
$env:RESUME_OUTPUT_ROOT = "D:\resume-output"
npm run render
```

## Markdown Extensions

```markdown
::左右 **Example Technology Ltd.** || **2024.07-2024.12**

::: start
**Example University**
:::
**Computer Science and Technology**
:::
**2021.09-2025.06**
::: end
```

See `plugins/local-resume-renderer/examples/example-resume.md` for the complete example.

## AI Coding Tool Integration

### Codex

```powershell
codex plugin marketplace add oneclickwork/local-resume-renderer
```

Install `local-resume-renderer` from the “本地简历工具” marketplace, then invoke:

```text
Use $resume-renderer to fit my latest resume on one page.
```

### Claude Code

```bash
claude plugin marketplace add oneclickwork/local-resume-renderer
claude plugin install local-resume-renderer@local-resume-tools --scope user
```

Run `/reload-plugins`, then invoke:

```text
/local-resume-renderer:resume-renderer fit my latest resume on one page
```

## Privacy

Do not commit real resumes, phone numbers, email addresses, messaging IDs, generated PDFs, or generated images to a public repository. This repository contains only anonymous sample data.

## License

[MIT](LICENSE)
