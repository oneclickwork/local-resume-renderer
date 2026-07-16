import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const defaultOutdir = process.env.RESUME_OUTPUT_ROOT
  ? path.resolve(process.env.RESUME_OUTPUT_ROOT)
  : path.join(os.homedir(), "Desktop", "resume");

const NORMAL_LAYOUT = Object.freeze({
  name: "normal",
  marginY: 9,
  lineHeight: 1.38,
  paragraphGap: 4,
  spacingScale: 1
});

const COMPACT_LAYOUT = Object.freeze({
  name: "compact",
  marginY: 6.5,
  lineHeight: 1.31,
  paragraphGap: 2.5,
  spacingScale: 0.85
});

function formatTimestamp(date = new Date()) {
  const pad = (value) => String(value).padStart(2, "0");
  return [
    date.getFullYear(),
    "-",
    pad(date.getMonth() + 1),
    "-",
    pad(date.getDate()),
    "_",
    pad(date.getHours()),
    "-",
    pad(date.getMinutes()),
    "-",
    pad(date.getSeconds())
  ].join("");
}

async function createVersionOutdir(rootDir) {
  await fs.mkdir(rootDir, { recursive: true });
  const baseName = formatTimestamp();

  for (let index = 0; index < 1000; index += 1) {
    const suffix = index === 0 ? "" : `-${String(index).padStart(2, "0")}`;
    const candidate = path.join(rootDir, `${baseName}${suffix}`);
    try {
      await fs.mkdir(candidate);
      return candidate;
    } catch (error) {
      if (error.code !== "EEXIST") {
        throw error;
      }
    }
  }

  throw new Error("Unable to create a unique timestamped output directory.");
}

const ICONS = {
  phone:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.6 10.8c1.6 3.2 3.4 5 6.6 6.6l2.2-2.2c.3-.3.8-.4 1.2-.3 1.3.4 2.6.6 4 .6.7 0 1.2.5 1.2 1.2v3.5c0 .7-.5 1.2-1.2 1.2C10.7 21.4 2.6 13.3 2.6 3.4c0-.7.5-1.2 1.2-1.2h3.5c.7 0 1.2.5 1.2 1.2 0 1.4.2 2.7.6 4 .1.4 0 .9-.3 1.2l-2.2 2.2z"/></svg>',
  email:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.8 5h16.4c1 0 1.8.8 1.8 1.8v10.4c0 1-.8 1.8-1.8 1.8H3.8c-1 0-1.8-.8-1.8-1.8V6.8C2 5.8 2.8 5 3.8 5zm8.2 8 8-5.2V7L12 12.1 4 7v.8l8 5.2z"/></svg>',
  profile:
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 12c2.5 0 4.5-2 4.5-4.5S14.5 3 12 3 7.5 5 7.5 7.5 9.5 12 12 12zm0 2c-4 0-7.5 2.1-7.5 4.7V21h15v-2.3C19.5 16.1 16 14 12 14z"/></svg>'
};

function parseArgs(argv) {
  const args = {
    input: null,
    outdir: defaultOutdir,
    compact: false,
    pageMarginY: null,
    lineHeight: null,
    fitPages: null
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--input" || arg === "-i") {
      args.input = argv[i + 1];
      i += 1;
    } else if (arg === "--outdir" || arg === "-o") {
      args.outdir = argv[i + 1];
      i += 1;
    } else if (arg === "--compact") {
      args.compact = true;
    } else if (arg === "--page-margin-y") {
      args.pageMarginY = parseNumberOption(arg, argv[i + 1], 3, 30);
      i += 1;
    } else if (arg === "--line-height") {
      args.lineHeight = parseNumberOption(arg, argv[i + 1], 1.1, 2);
      i += 1;
    } else if (arg === "--fit-pages") {
      args.fitPages = parseNumberOption(arg, argv[i + 1], 1, 20, true);
      i += 1;
    } else if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }

  return args;
}

function parseNumberOption(option, value, minimum, maximum, integer = false) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < minimum || parsed > maximum) {
    throw new Error(`${option} must be between ${minimum} and ${maximum}.`);
  }
  if (integer && !Number.isInteger(parsed)) {
    throw new Error(`${option} must be an integer.`);
  }
  return parsed;
}

function printHelp() {
  console.log(`Usage:
  npm run render
  npm run render -- --input resume.md --outdir "%USERPROFILE%\\Desktop\\resume"
  npm run render -- --compact
  npm run render -- --page-margin-y 6 --line-height 1.30
  npm run render -- --fit-pages 1

Defaults:
  input  Markdown from the latest version directory, then the project root
  outdir ${defaultOutdir}\\<YYYY-MM-DD_HH-mm-ss>

Layout options:
  --compact             Use a compact spacing preset without reducing font size
  --page-margin-y <mm>  Set PDF top and bottom margins (3-30 mm)
  --line-height <ratio> Set paragraph and list line height (1.1-2.0)
  --fit-pages <count>   Automatically tighten spacing to fit the target page count`);
}

function resolveLayoutOptions(args) {
  const preset = args.compact ? COMPACT_LAYOUT : NORMAL_LAYOUT;
  return {
    ...preset,
    marginY: args.pageMarginY ?? preset.marginY,
    lineHeight: args.lineHeight ?? preset.lineHeight
  };
}

function buildLayoutCss(layout) {
  const screenMarginY = (layout.marginY * 96) / 25.4;
  const scale = layout.spacingScale;
  return `
@page { size: A4; margin: ${layout.marginY}mm 8mm; }
.page { padding-top: ${screenMarginY}px; padding-bottom: ${screenMarginY}px; }
.intent-line { margin-bottom: ${13 * scale}px; }
h2 { margin-top: ${12 * scale}px; margin-bottom: ${7 * scale}px; padding-bottom: ${5 * scale}px; }
.info-row { margin-bottom: ${5 * scale}px; }
p { line-height: ${layout.lineHeight}; margin-bottom: ${layout.paragraphGap + 1}px; }
.minor-heading { margin-top: ${4 * scale}px; margin-bottom: ${1 * scale}px; }
.label-line { margin-top: ${3 * scale}px; margin-bottom: ${2 * scale}px; }
ul { margin-top: ${2 * scale}px; margin-bottom: ${6 * scale}px; }
li { line-height: ${layout.lineHeight}; margin-bottom: ${layout.paragraphGap}px; }
`;
}

function buildFitLayouts(baseLayout) {
  const profiles = [
    baseLayout,
    {
      name: "fit-1",
      marginY: Math.min(baseLayout.marginY, 7.5),
      lineHeight: Math.min(baseLayout.lineHeight, 1.34),
      paragraphGap: Math.min(baseLayout.paragraphGap, 3.25),
      spacingScale: Math.min(baseLayout.spacingScale, 0.93)
    },
    {
      name: "fit-2",
      marginY: Math.min(baseLayout.marginY, 6),
      lineHeight: Math.min(baseLayout.lineHeight, 1.29),
      paragraphGap: Math.min(baseLayout.paragraphGap, 2),
      spacingScale: Math.min(baseLayout.spacingScale, 0.82)
    },
    {
      name: "fit-3",
      marginY: Math.min(baseLayout.marginY, 4.5),
      lineHeight: Math.min(baseLayout.lineHeight, 1.22),
      paragraphGap: Math.min(baseLayout.paragraphGap, 1),
      spacingScale: Math.min(baseLayout.spacingScale, 0.72)
    }
  ];

  return profiles.filter((layout, index) => {
    const signature = [layout.marginY, layout.lineHeight, layout.paragraphGap, layout.spacingScale].join("|");
    return profiles.findIndex((candidate) =>
      [candidate.marginY, candidate.lineHeight, candidate.paragraphGap, candidate.spacingScale].join("|") ===
      signature
    ) === index;
  });
}

function interpolateLayout(looser, tighter, ratio) {
  const interpolate = (key) =>
    Number((looser[key] + (tighter[key] - looser[key]) * ratio).toFixed(4));
  return {
    name: "fit-auto",
    marginY: interpolate("marginY"),
    lineHeight: interpolate("lineHeight"),
    paragraphGap: interpolate("paragraphGap"),
    spacingScale: interpolate("spacingScale")
  };
}

function chooseMarkdownFile(files) {
  const sorted = files.sort((a, b) => a.localeCompare(b, "zh-Hans-CN"));
  return sorted.find((name) => name.includes("简历")) ?? sorted[0] ?? null;
}

async function findLatestVersionInput(outdirRoot) {
  let entries;
  try {
    entries = await fs.readdir(outdirRoot, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") {
      return null;
    }
    throw error;
  }

  const directories = await Promise.all(
    entries
      .filter((entry) => entry.isDirectory())
      .map(async (entry) => {
        const fullPath = path.join(outdirRoot, entry.name);
        const stat = await fs.stat(fullPath);
        return { fullPath, modifiedAt: stat.mtimeMs };
      })
  );

  directories.sort((a, b) => b.modifiedAt - a.modifiedAt);
  for (const directory of directories) {
    const files = await fs.readdir(directory.fullPath, { withFileTypes: true });
    const markdownName = chooseMarkdownFile(
      files
        .filter((entry) => entry.isFile())
        .map((entry) => entry.name)
        .filter((name) => name.toLowerCase().endsWith(".md"))
        .filter((name) => name.toLowerCase() !== "readme.md")
    );
    if (markdownName) {
      return path.join(directory.fullPath, markdownName);
    }
  }

  return null;
}

async function findDefaultInput(outdirRoot) {
  const latestVersionInput = await findLatestVersionInput(outdirRoot);
  if (latestVersionInput) {
    return latestVersionInput;
  }

  for (const directory of [projectRoot, path.join(projectRoot, "examples")]) {
    let entries;
    try {
      entries = await fs.readdir(directory, { withFileTypes: true });
    } catch (error) {
      if (error.code === "ENOENT") {
        continue;
      }
      throw error;
    }

    const markdownName = chooseMarkdownFile(
      entries
        .filter((entry) => entry.isFile())
        .map((entry) => entry.name)
        .filter((name) => name.toLowerCase().endsWith(".md"))
        .filter((name) => name.toLowerCase() !== "readme.md")
    );
    if (markdownName) {
      return path.join(directory, markdownName);
    }
  }

  throw new Error(
    "No Markdown resume found in the latest version directory, project root, or examples directory."
  );
}

function normalizeMarkdown(markdown) {
  return markdown
    .replace(/^\uFEFF/, "")
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .map((line) => {
      const trimmedRight = line.replace(/\s+$/u, "");
      const trimmedLeft = trimmedRight.replace(/^\s+/u, "");
      return trimmedLeft.replace(/^(?:-\s*){3,}(#\s+)/u, "$1");
    });
}

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function inlineMarkdown(value) {
  return escapeHtml(value).replace(/\*\*(.+?)\*\*/gu, "<strong>$1</strong>");
}

function stripInlineMarkdown(value) {
  return value.replace(/\*\*(.+?)\*\*/gu, "$1").trim();
}

function iconMarkup(name) {
  return ICONS[name] ?? ICONS.profile;
}

function renderContactLine(line) {
  const parts = line
    .split(/[｜|]/u)
    .map((part) => part.trim())
    .filter(Boolean);

  const rendered = parts.map((part) => {
    const match = part.match(/^icon:([a-zA-Z0-9_-]+)\s+(.+)$/u);
    if (!match) {
      return `<span class="contact-item">${inlineMarkdown(part)}</span>`;
    }

    return [
      '<span class="contact-item">',
      `<span class="contact-icon">${iconMarkup(match[1])}</span>`,
      `<span>${inlineMarkdown(match[2])}</span>`,
      "</span>"
    ].join("");
  });

  return `<div class="contact-line">${rendered.join('<span class="contact-separator">|</span>')}</div>`;
}

function renderHeaderLine(line) {
  if (line.includes("icon:")) {
    return renderContactLine(line);
  }

  return `<div class="intent-line">${inlineMarkdown(line)}</div>`;
}

function renderInfoRow(cells) {
  const className = `info-row cols-${Math.min(Math.max(cells.length, 1), 4)}`;
  const renderedCells = cells
    .map((cell) => {
      const content = cell
        .map((line) => inlineMarkdown(line))
        .join("<br>");
      return `<div class="info-cell">${content}</div>`;
    })
    .join("");

  return `<div class="${className}">${renderedCells}</div>`;
}

function parseInlineAlignRow(line) {
  const match = line.match(/^::(?:lr|左右|对齐)\s+(.+?)\s+\|\|\s+(.+)$/u);
  if (!match) {
    return null;
  }

  return [[match[1].trim()], [match[2].trim()]];
}

function renderParagraph(line) {
  const text = line.trim();
  if (!text) {
    return "";
  }

  if (/^\*\*.+\*\*$/u.test(text)) {
    return `<p class="minor-heading">${inlineMarkdown(text)}</p>`;
  }

  if (/^\*\*.+?\*\*[：:]\s*$/u.test(text)) {
    return `<p class="label-line">${inlineMarkdown(text)}</p>`;
  }

  return `<p>${inlineMarkdown(text)}</p>`;
}

function parseResumeMarkdown(markdown) {
  const lines = normalizeMarkdown(markdown);
  const headerLines = [];
  const body = [];
  let title = "";
  let hasBodyStarted = false;
  let isListOpen = false;

  const closeList = () => {
    if (isListOpen) {
      body.push("</ul>");
      isListOpen = false;
    }
  };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i].trim();

    if (!line) {
      closeList();
      continue;
    }

    const headingOne = line.match(/^#\s+(.+)$/u);
    if (headingOne && !title) {
      title = stripInlineMarkdown(headingOne[1]);
      continue;
    }

    const headingTwo = line.match(/^##\s+(.+)$/u);
    if (headingTwo) {
      hasBodyStarted = true;
      closeList();
      body.push(`<h2>${inlineMarkdown(headingTwo[1])}</h2>`);
      continue;
    }

    if (!hasBodyStarted) {
      headerLines.push(renderHeaderLine(line));
      continue;
    }

    const inlineAlignRow = parseInlineAlignRow(line);
    if (inlineAlignRow) {
      closeList();
      body.push(renderInfoRow(inlineAlignRow));
      continue;
    }

    if (/^:::\s*(?:start|左右|对齐|align|lr)\s*$/u.test(line)) {
      closeList();
      const cells = [];
      let currentCell = [];

      for (i += 1; i < lines.length; i += 1) {
        const rowLine = lines[i].trim();
        if (!rowLine) {
          continue;
        }

        if (rowLine === "::: end") {
          if (currentCell.length > 0) {
            cells.push(currentCell);
          }
          break;
        }

        if (rowLine === ":::") {
          cells.push(currentCell);
          currentCell = [];
          continue;
        }

        currentCell.push(rowLine);
      }

      if (cells.length > 0) {
        body.push(renderInfoRow(cells));
      }
      continue;
    }

    const listItem = line.match(/^[-*]\s+(.+)$/u);
    if (listItem) {
      if (!isListOpen) {
        body.push("<ul>");
        isListOpen = true;
      }
      body.push(`<li>${inlineMarkdown(listItem[1])}</li>`);
      continue;
    }

    closeList();
    body.push(renderParagraph(line));
  }

  closeList();

  return {
    title: title || "简历",
    headerHtml: headerLines.join("\n"),
    bodyHtml: body.join("\n")
  };
}

async function buildHtml(markdown, cssPath, layout) {
  const css = await fs.readFile(cssPath, "utf8");
  const resume = parseResumeMarkdown(markdown);

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(resume.title)}</title>
  <style>${css}</style>
  <style id="render-layout-options">${buildLayoutCss(layout)}</style>
</head>
<body>
  <main class="page">
    <header class="resume-header">
      <h1>${escapeHtml(resume.title)}</h1>
      ${resume.headerHtml}
    </header>
    <section class="resume-body">
      ${resume.bodyHtml}
    </section>
  </main>
</body>
</html>`;
}

async function loadPlaywright() {
  try {
    const playwright = await import("playwright");
    return playwright.chromium;
  } catch (error) {
    throw new Error(
      "Playwright is not installed. Run `npm install` first, then retry `npm run render`."
    );
  }
}

function countPdfPages(pdfBuffer) {
  const pdfText = pdfBuffer.toString("latin1");
  const pageCount = (pdfText.match(/\/Type\s*\/Page\b/gu) ?? []).length;
  if (pageCount === 0) {
    throw new Error("Unable to determine the generated PDF page count.");
  }
  return pageCount;
}

async function applyLayout(page, layout) {
  const css = buildLayoutCss(layout);
  await page.evaluate((layoutCss) => {
    const style = document.querySelector("#render-layout-options");
    if (!style) {
      throw new Error("Layout options style element was not found.");
    }
    style.textContent = layoutCss;
  }, css);
}

async function renderPdfBuffer(page) {
  return page.pdf({
    format: "A4",
    printBackground: true,
    preferCSSPageSize: true
  });
}

async function renderWithPlaywright(htmlPath, pdfPath, pngPath, jpgPath, options) {
  const chromium = await loadPlaywright();
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 794, height: 1123 },
    deviceScaleFactor: 1
  });

  try {
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });

    const layouts = options.fitPages
      ? buildFitLayouts(options.layout)
      : [options.layout];
    let selected = null;
    let previousFailed = null;

    for (const layout of layouts) {
      await applyLayout(page, layout);
      const pdfBuffer = await renderPdfBuffer(page);
      const pageCount = countPdfPages(pdfBuffer);
      selected = { layout, pdfBuffer, pageCount };

      if (!options.fitPages || pageCount <= options.fitPages) {
        if (options.fitPages && previousFailed) {
          let looser = previousFailed.layout;
          let tighter = selected.layout;

          for (let attempt = 0; attempt < 7; attempt += 1) {
            const candidate = interpolateLayout(looser, tighter, 0.5);
            await applyLayout(page, candidate);
            const candidatePdf = await renderPdfBuffer(page);
            const candidatePages = countPdfPages(candidatePdf);

            if (candidatePages <= options.fitPages) {
              tighter = candidate;
              selected = {
                layout: candidate,
                pdfBuffer: candidatePdf,
                pageCount: candidatePages
              };
            } else {
              looser = candidate;
            }
          }
        }
        break;
      }

      previousFailed = selected;
    }

    await applyLayout(page, selected.layout);
    await fs.writeFile(pdfPath, selected.pdfBuffer);
    await fs.writeFile(htmlPath, await page.content(), "utf8");

    await page.screenshot({
      path: pngPath,
      fullPage: true,
      type: "png"
    });

    await page.screenshot({
      path: jpgPath,
      fullPage: true,
      type: "jpeg",
      quality: 92
    });

    return {
      layout: selected.layout,
      pageCount: selected.pageCount,
      targetPages: options.fitPages,
      targetMet: !options.fitPages || selected.pageCount <= options.fitPages
    };
  } finally {
    await browser.close();
  }
}

async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function findPythonExecutable() {
  if (process.env.RESUME_RENDERER_PYTHON) {
    return process.env.RESUME_RENDERER_PYTHON;
  }

  const bundled = path.join(
    os.homedir(),
    ".cache",
    "codex-runtimes",
    "codex-primary-runtime",
    "dependencies",
    "python",
    "python.exe"
  );

  if (await fileExists(bundled)) {
    return bundled;
  }

  return "python";
}

async function renderWithPythonFallback(inputPath, outdir, args) {
  const python = await findPythonExecutable();
  const script = path.join(__dirname, "render_reportlab.py");
  const pythonArgs = [script, "--input", inputPath, "--outdir", outdir, "--exact-outdir"];
  if (args.compact) {
    pythonArgs.push("--compact");
  }
  if (args.pageMarginY !== null) {
    pythonArgs.push("--page-margin-y", String(args.pageMarginY));
  }
  if (args.lineHeight !== null) {
    pythonArgs.push("--line-height", String(args.lineHeight));
  }
  if (args.fitPages !== null) {
    pythonArgs.push("--fit-pages", String(args.fitPages));
  }
  const result = spawnSync(
    python,
    pythonArgs,
    {
      cwd: projectRoot,
      stdio: "inherit",
      shell: false
    }
  );

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    throw new Error(`Python fallback renderer failed with exit code ${result.status}.`);
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    return;
  }

  const outdirRoot = path.resolve(projectRoot, args.outdir);
  const inputPath = args.input
    ? path.resolve(projectRoot, args.input)
    : await findDefaultInput(outdirRoot);
  const outdir = await createVersionOutdir(outdirRoot);
  const cssPath = path.join(__dirname, "style.css");
  const layout = resolveLayoutOptions(args);
  const markdownSnapshotPath = path.join(outdir, path.basename(inputPath));
  const htmlPath = path.join(outdir, "resume.html");
  const pdfPath = path.join(outdir, "resume.pdf");
  const pngPath = path.join(outdir, "resume.png");
  const jpgPath = path.join(outdir, "resume.jpg");

  const markdown = await fs.readFile(inputPath, "utf8");
  const html = await buildHtml(markdown, cssPath, layout);

  await fs.mkdir(outdir, { recursive: true });
  await fs.copyFile(inputPath, markdownSnapshotPath);
  await fs.writeFile(htmlPath, html, "utf8");
  let renderResult = null;
  try {
    renderResult = await renderWithPlaywright(htmlPath, pdfPath, pngPath, jpgPath, {
      layout,
      fitPages: args.fitPages
    });
  } catch (error) {
    const firstLine = String(error.message).split(/\r?\n/u)[0];
    console.log(`Playwright render unavailable: ${firstLine}`);
    console.log("Falling back to ReportLab + Poppler renderer.");
    await renderWithPythonFallback(inputPath, outdir, args);
  }

  if (renderResult) {
    const status = renderResult.targetMet ? "target met" : "target not met";
    const target = renderResult.targetPages
      ? `, target=${renderResult.targetPages} (${status})`
      : "";
    console.log(
      `Layout ${renderResult.layout.name}: pages=${renderResult.pageCount}, ` +
        `marginY=${renderResult.layout.marginY}mm, lineHeight=${renderResult.layout.lineHeight}${target}`
    );
  }

  console.log(`Rendered:
  Input ${inputPath}
  MD   ${markdownSnapshotPath}
  HTML ${path.relative(projectRoot, htmlPath)}
  PDF  ${path.relative(projectRoot, pdfPath)}
  PNG  ${path.relative(projectRoot, pngPath)}
  JPG  ${path.relative(projectRoot, jpgPath)}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
