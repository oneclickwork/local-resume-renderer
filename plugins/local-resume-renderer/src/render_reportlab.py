from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = Path(os.environ.get("RESUME_OUTPUT_ROOT", Path.home() / "Desktop" / "resume"))
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 22.5
RIGHT_MARGIN = 22.5
TOP_MARGIN = 9 * 72 / 25.4
BOTTOM_MARGIN = 9 * 72 / 25.4
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
LINE_HEIGHT = 1.38
PARAGRAPH_GAP = 3.0
SPACING_SCALE = 1.0

NORMAL_LAYOUT = {
    "name": "normal",
    "margin_y": 9.0,
    "line_height": 1.38,
    "paragraph_gap": 3.0,
    "spacing_scale": 1.0,
}
COMPACT_LAYOUT = {
    "name": "compact",
    "margin_y": 6.5,
    "line_height": 1.31,
    "paragraph_gap": 2.0,
    "spacing_scale": 0.85,
}

FONT_NORMAL = "ResumeMSYH"
FONT_BOLD = "ResumeMSYHBold"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Markdown resume to PDF and PNG.")
    parser.add_argument("--input", "-i", default=None, help="Markdown resume path.")
    parser.add_argument("--outdir", "-o", default=str(DEFAULT_OUTDIR), help="Output directory.")
    parser.add_argument(
        "--exact-outdir",
        action="store_true",
        help="Use --outdir directly instead of creating a timestamped child directory.",
    )
    parser.add_argument("--compact", action="store_true", help="Use compact spacing.")
    parser.add_argument("--page-margin-y", type=float, default=None, help="Top/bottom margin in mm.")
    parser.add_argument("--line-height", type=float, default=None, help="Body line-height ratio.")
    parser.add_argument("--fit-pages", type=int, default=None, help="Target PDF page count.")
    return parser.parse_args()


def resolve_layout_options(args: argparse.Namespace) -> dict[str, float | str]:
    preset = COMPACT_LAYOUT if args.compact else NORMAL_LAYOUT
    layout = dict(preset)
    if args.page_margin_y is not None:
        if not 3 <= args.page_margin_y <= 30:
            raise ValueError("--page-margin-y must be between 3 and 30.")
        layout["margin_y"] = args.page_margin_y
    if args.line_height is not None:
        if not 1.1 <= args.line_height <= 2:
            raise ValueError("--line-height must be between 1.1 and 2.0.")
        layout["line_height"] = args.line_height
    if args.fit_pages is not None and not 1 <= args.fit_pages <= 20:
        raise ValueError("--fit-pages must be between 1 and 20.")
    return layout


def build_fit_layouts(base: dict[str, float | str]) -> list[dict[str, float | str]]:
    limits = [
        ("fit-1", 7.5, 1.34, 2.5, 0.93),
        ("fit-2", 6.0, 1.29, 1.5, 0.82),
        ("fit-3", 4.5, 1.22, 0.75, 0.72),
    ]
    layouts = [dict(base)]
    for name, margin_y, line_height, paragraph_gap, spacing_scale in limits:
        layouts.append(
            {
                "name": name,
                "margin_y": min(float(base["margin_y"]), margin_y),
                "line_height": min(float(base["line_height"]), line_height),
                "paragraph_gap": min(float(base["paragraph_gap"]), paragraph_gap),
                "spacing_scale": min(float(base["spacing_scale"]), spacing_scale),
            }
        )

    unique = []
    signatures = set()
    for layout in layouts:
        signature = tuple(layout[key] for key in ("margin_y", "line_height", "paragraph_gap", "spacing_scale"))
        if signature not in signatures:
            signatures.add(signature)
            unique.append(layout)
    return unique


def apply_layout(layout: dict[str, float | str]) -> None:
    global TOP_MARGIN, BOTTOM_MARGIN, LINE_HEIGHT, PARAGRAPH_GAP, SPACING_SCALE
    TOP_MARGIN = float(layout["margin_y"]) * 72 / 25.4
    BOTTOM_MARGIN = TOP_MARGIN
    LINE_HEIGHT = float(layout["line_height"])
    PARAGRAPH_GAP = float(layout["paragraph_gap"])
    SPACING_SCALE = float(layout["spacing_scale"])


def create_version_outdir(root_dir: Path) -> Path:
    root_dir.mkdir(parents=True, exist_ok=True)
    base_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    for index in range(1000):
        suffix = "" if index == 0 else f"-{index:02d}"
        candidate = root_dir / f"{base_name}{suffix}"
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue

    raise RuntimeError("Unable to create a unique timestamped output directory.")


def choose_markdown_file(files: list[Path]) -> Path | None:
    sorted_files = sorted(files, key=lambda path: path.name)
    return next((file for file in sorted_files if "简历" in file.name), None) or (
        sorted_files[0] if sorted_files else None
    )


def find_latest_version_input(outdir_root: Path) -> Path | None:
    if not outdir_root.exists():
        return None

    directories = sorted(
        (entry for entry in outdir_root.iterdir() if entry.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for directory in directories:
        markdown_file = choose_markdown_file(
            [
                file
                for file in directory.iterdir()
                if file.is_file()
                and file.suffix.lower() == ".md"
                and file.name.lower() != "readme.md"
            ]
        )
        if markdown_file:
            return markdown_file

    return None


def find_default_input(outdir_root: Path) -> Path:
    latest_version_input = find_latest_version_input(outdir_root)
    if latest_version_input:
        return latest_version_input

    for directory in (PROJECT_ROOT, PROJECT_ROOT / "examples"):
        if not directory.exists():
            continue
        markdown_files = sorted(
            [
                file
                for file in directory.iterdir()
                if file.is_file()
                and file.suffix.lower() == ".md"
                and file.name.lower() != "readme.md"
            ],
            key=lambda path: path.name,
        )
        if markdown_files:
            return choose_markdown_file(markdown_files)

    raise FileNotFoundError(
        "No Markdown resume found in the latest version directory, project root, or examples directory."
    )


def register_fonts() -> None:
    font_candidates = [
        (FONT_NORMAL, Path(r"C:\Windows\Fonts\msyh.ttc")),
        (FONT_BOLD, Path(r"C:\Windows\Fonts\msyhbd.ttc")),
    ]

    fallback_candidates = [
        (FONT_NORMAL, Path(r"C:\Windows\Fonts\simhei.ttf")),
        (FONT_BOLD, Path(r"C:\Windows\Fonts\simhei.ttf")),
    ]

    try:
        for name, file in font_candidates:
            pdfmetrics.registerFont(TTFont(name, str(file)))
    except Exception:
        for name, file in fallback_candidates:
            pdfmetrics.registerFont(TTFont(name, str(file)))

    pdfmetrics.registerFontFamily(
        "ResumeMSYH",
        normal=FONT_NORMAL,
        bold=FONT_BOLD,
        italic=FONT_NORMAL,
        boldItalic=FONT_BOLD,
    )


def normalize_markdown(markdown: str) -> list[str]:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff").split("\n")
    normalized = []
    for line in lines:
        value = line.rstrip()
        value = re.sub(r"^\s+", "", value)
        value = re.sub(r"^(?:-\s*){3,}(#\s+)", r"\1", value)
        normalized.append(value)
    return normalized


def inline_markdown(value: str) -> str:
    escaped = html.escape(value, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)


def strip_inline_markdown(value: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", value).strip()


@dataclass
class ResumeParts:
    title: str
    header_lines: list[str]
    body_items: list[tuple[str, object]]


@dataclass
class ContactItem:
    icon: str | None
    text: str


class ContactLine(Flowable):
    def __init__(self, items: list[ContactItem]):
        super().__init__()
        self.items = items
        self.font_size = 10.5
        self.height = 13
        self.icon_size = 9
        self.icon_gap = 4
        self.separator_gap = 8
        self.color = colors.HexColor("#666666")

    def _item_width(self, item: ContactItem) -> float:
        text_width = pdfmetrics.stringWidth(item.text, FONT_NORMAL, self.font_size)
        if item.icon:
            return self.icon_size + self.icon_gap + text_width
        return text_width

    def wrap(self, avail_width, avail_height):
        items_width = sum(self._item_width(item) for item in self.items)
        separators_width = 0
        if len(self.items) > 1:
            separators_width = (len(self.items) - 1) * (
                pdfmetrics.stringWidth("|", FONT_NORMAL, self.font_size) + self.separator_gap * 2
            )
        self.width = min(avail_width, items_width + separators_width)
        self.available_width = avail_width
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(self.color)
        canvas.setStrokeColor(self.color)
        canvas.setLineWidth(1)
        canvas.setFont(FONT_NORMAL, self.font_size)

        total_width = sum(self._item_width(item) for item in self.items)
        if len(self.items) > 1:
            total_width += (len(self.items) - 1) * (
                pdfmetrics.stringWidth("|", FONT_NORMAL, self.font_size) + self.separator_gap * 2
            )
        x = max(0, (getattr(self, "available_width", self.width) - total_width) / 2)
        baseline = 2

        for index, item in enumerate(self.items):
            if item.icon:
                self._draw_icon(canvas, item.icon, x, baseline + 1)
                x += self.icon_size + self.icon_gap

            canvas.drawString(x, baseline, item.text)
            x += pdfmetrics.stringWidth(item.text, FONT_NORMAL, self.font_size)

            if index != len(self.items) - 1:
                x += self.separator_gap
                canvas.drawString(x, baseline, "|")
                x += pdfmetrics.stringWidth("|", FONT_NORMAL, self.font_size) + self.separator_gap

        canvas.restoreState()

    def _draw_icon(self, canvas, icon: str, x: float, y: float) -> None:
        size = self.icon_size
        if icon == "email":
            canvas.rect(x, y + 1, size, size - 2, stroke=1, fill=0)
            canvas.line(x, y + size - 1, x + size / 2, y + size / 2)
            canvas.line(x + size, y + size - 1, x + size / 2, y + size / 2)
            return

        if icon == "profile":
            canvas.circle(x + size / 2, y + size - 2.5, 2.4, stroke=0, fill=1)
            canvas.roundRect(x + 1.2, y + 1, size - 2.4, 4.6, 1.8, stroke=0, fill=1)
            return

        canvas.saveState()
        canvas.translate(x + 2, y + 1)
        canvas.rotate(-32)
        canvas.roundRect(0, 0, 3.2, size, 1.4, stroke=0, fill=1)
        canvas.restoreState()


def parse_resume(markdown: str) -> ResumeParts:
    lines = normalize_markdown(markdown)
    title = ""
    header_lines: list[str] = []
    body_items: list[tuple[str, object]] = []
    has_body_started = False

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if not line:
            continue

        heading_one = re.match(r"^#\s+(.+)$", line)
        if heading_one and not title:
            title = strip_inline_markdown(heading_one.group(1))
            continue

        heading_two = re.match(r"^##\s+(.+)$", line)
        if heading_two:
            has_body_started = True
            body_items.append(("h2", heading_two.group(1)))
            continue

        if not has_body_started:
            header_lines.append(line)
            continue

        inline_align_row = re.match(r"^::(?:lr|左右|对齐)\s+(.+?)\s+\|\|\s+(.+)$", line)
        if inline_align_row:
            body_items.append(
                ("row", [[inline_align_row.group(1).strip()], [inline_align_row.group(2).strip()]])
            )
            continue

        if re.match(r"^:::\s*(?:start|左右|对齐|align|lr)\s*$", line):
            cells: list[list[str]] = []
            current_cell: list[str] = []
            while i < len(lines):
                row_line = lines[i].strip()
                i += 1
                if not row_line:
                    continue
                if row_line == "::: end":
                    if current_cell:
                        cells.append(current_cell)
                    break
                if row_line == ":::":
                    cells.append(current_cell)
                    current_cell = []
                    continue
                current_cell.append(row_line)
            if cells:
                body_items.append(("row", cells))
            continue

        list_item = re.match(r"^[-*]\s+(.+)$", line)
        if list_item:
            body_items.append(("li", list_item.group(1)))
            continue

        body_items.append(("p", line))

    return ResumeParts(title=title or "简历", header_lines=header_lines, body_items=body_items)


def make_styles() -> dict[str, ParagraphStyle]:
    body_leading = 14 * LINE_HEIGHT / 1.38
    base = {
        "wordWrap": "CJK",
        "splitLongWords": True,
    }
    return {
        "name": ParagraphStyle(
            "name",
            **base,
            fontName=FONT_BOLD,
            fontSize=16.5,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=7 * SPACING_SCALE,
            textColor=colors.HexColor("#333333"),
        ),
        "contact": ParagraphStyle(
            "contact",
            **base,
            fontName=FONT_NORMAL,
            fontSize=10.5,
            leading=13,
            alignment=TA_CENTER,
            spaceAfter=2 * SPACING_SCALE,
            textColor=colors.HexColor("#666666"),
        ),
        "intent": ParagraphStyle(
            "intent",
            **base,
            fontName=FONT_NORMAL,
            fontSize=10.5,
            leading=13,
            alignment=TA_CENTER,
            spaceAfter=8 * SPACING_SCALE,
            textColor=colors.HexColor("#555555"),
        ),
        "section": ParagraphStyle(
            "section",
            **base,
            fontName=FONT_BOLD,
            fontSize=12,
            leading=14,
            alignment=TA_LEFT,
            spaceBefore=4 * SPACING_SCALE,
            spaceAfter=1 * SPACING_SCALE,
            keepWithNext=True,
            textColor=colors.HexColor("#111111"),
        ),
        "normal": ParagraphStyle(
            "normal",
            **base,
            fontName=FONT_NORMAL,
            fontSize=10.5,
            leading=body_leading,
            alignment=TA_JUSTIFY,
            spaceBefore=0,
            spaceAfter=PARAGRAPH_GAP,
            textColor=colors.HexColor("#555555"),
        ),
        "minor": ParagraphStyle(
            "minor",
            **base,
            fontName=FONT_BOLD,
            fontSize=10.5,
            leading=13,
            spaceBefore=1 * SPACING_SCALE,
            spaceAfter=1 * SPACING_SCALE,
            keepWithNext=True,
            textColor=colors.HexColor("#2d2d2d"),
        ),
        "bullet": ParagraphStyle(
            "bullet",
            **base,
            fontName=FONT_NORMAL,
            fontSize=10.5,
            leading=body_leading,
            alignment=TA_JUSTIFY,
            leftIndent=12,
            firstLineIndent=0,
            bulletIndent=0,
            spaceBefore=0,
            spaceAfter=PARAGRAPH_GAP,
            textColor=colors.HexColor("#555555"),
        ),
        "cell": ParagraphStyle(
            "cell",
            **base,
            fontName=FONT_NORMAL,
            fontSize=10.5,
            leading=13,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.HexColor("#333333"),
        ),
        "cell_right": ParagraphStyle(
            "cell_right",
            **base,
            fontName=FONT_NORMAL,
            fontSize=10.5,
            leading=13,
            alignment=TA_RIGHT,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.HexColor("#333333"),
        ),
    }


def parse_contact_items(line: str) -> list[ContactItem]:
    parts = [part.strip() for part in re.split(r"[｜|]", line) if part.strip()]
    items = []
    for part in parts:
        match = re.match(r"^icon:([a-zA-Z0-9_-]+)\s+(.+)$", part)
        if match:
            items.append(ContactItem(icon=match.group(1), text=strip_inline_markdown(match.group(2))))
        else:
            items.append(ContactItem(icon=None, text=strip_inline_markdown(part)))
    return items


def build_story(parts: ResumeParts) -> list:
    styles = make_styles()
    story: list = [Paragraph(html.escape(parts.title), styles["name"])]

    for line in parts.header_lines:
        if "icon:" in line:
            story.append(ContactLine(parse_contact_items(line)))
            story.append(Spacer(1, 2 * SPACING_SCALE))
        else:
            story.append(Paragraph(inline_markdown(line), styles["intent"]))

    previous_was_li = False
    for item_type, payload in parts.body_items:
        if item_type != "li" and previous_was_li:
            story.append(Spacer(1, 1 * SPACING_SCALE))
        previous_was_li = item_type == "li"

        if item_type == "h2":
            heading = Paragraph(inline_markdown(str(payload)), styles["section"])
            rule = HRFlowable(
                width="100%",
                thickness=0.75,
                color=colors.HexColor("#222222"),
                spaceBefore=1 * SPACING_SCALE,
                spaceAfter=5 * SPACING_SCALE,
            )
            story.append(heading)
            story.append(rule)
            continue

        if item_type == "row":
            cells = payload
            col_width_map = {
                2: [CONTENT_WIDTH * 0.5, CONTENT_WIDTH * 0.5],
                3: [CONTENT_WIDTH * 0.44, CONTENT_WIDTH * 0.33, CONTENT_WIDTH * 0.23],
                4: [
                    CONTENT_WIDTH * 0.31,
                    CONTENT_WIDTH * 0.18,
                    CONTENT_WIDTH * 0.28,
                    CONTENT_WIDTH * 0.23,
                ],
            }
            widths = col_width_map.get(len(cells), [CONTENT_WIDTH / len(cells)] * len(cells))
            table_cells = []
            for index, cell in enumerate(cells):
                style = styles["cell_right"] if index == len(cells) - 1 else styles["cell"]
                cell_html = "<br/>".join(inline_markdown(line) for line in cell)
                table_cells.append(Paragraph(cell_html, style))
            table = Table([table_cells], colWidths=widths, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * SPACING_SCALE),
                    ]
                )
            )
            story.append(table)
            continue

        if item_type == "li":
            story.append(Paragraph(inline_markdown(str(payload)), styles["bullet"], bulletText="•"))
            continue

        line = str(payload).strip()
        style = styles["minor"] if re.match(r"^\*\*.+\*\*$", line) else styles["normal"]
        story.append(Paragraph(inline_markdown(line), style))

    return story


def story_height(story: list) -> float:
    total = TOP_MARGIN + BOTTOM_MARGIN
    for flowable in story:
        if hasattr(flowable, "wrap"):
            _, height = flowable.wrap(CONTENT_WIDTH, 100000)
        else:
            height = 0
        total += getattr(flowable, "getSpaceBefore", lambda: 0)()
        total += height
        total += getattr(flowable, "getSpaceAfter", lambda: 0)()
    return max(total + 6, PAGE_HEIGHT)


def build_pdf(story: list, pdf_path: Path, pagesize=A4) -> None:
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=pagesize,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title="Resume",
        author="local-resume-renderer",
    )
    doc.build(story)


def count_pdf_pages(pdf_path: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page\b", pdf_path.read_bytes()))


def render_png_from_pdf(pdf_path: Path, png_path: Path, tmp_dir: Path) -> None:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("pdftoppm was not found in PATH; install Poppler or MiKTeX Poppler tools.")

    tmp_dir.mkdir(parents=True, exist_ok=True)
    prefix = tmp_dir / "resume_png"
    for old_file in tmp_dir.glob("resume_png*.png"):
        old_file.unlink()

    result = subprocess.run(
        [pdftoppm, "-png", "-r", "96", "-singlefile", str(pdf_path), str(prefix)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise subprocess.CalledProcessError(result.returncode, result.args)

    generated = prefix.with_suffix(".png")
    if not generated.exists():
        raise RuntimeError("pdftoppm did not produce a PNG file.")
    Image.open(generated).save(png_path)


def render_jpg_from_png(png_path: Path, jpg_path: Path) -> None:
    image = Image.open(png_path)
    if image.mode != "RGB":
        background = Image.new("RGB", image.size, "white")
        if image.mode in ("RGBA", "LA"):
            background.paste(image, mask=image.getchannel("A"))
        else:
            background.paste(image.convert("RGB"))
        image = background
    image.save(jpg_path, quality=92, optimize=True)


def display_path(file_path: Path) -> str:
    try:
        return str(file_path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(file_path)


def main() -> None:
    args = parse_args()
    outdir_root = Path(args.outdir).resolve()
    input_path = Path(args.input).resolve() if args.input else find_default_input(outdir_root)
    outdir = outdir_root if args.exact_outdir else create_version_outdir(outdir_root)
    tmp_dir = PROJECT_ROOT / "tmp" / "pdfs"

    output_pdf = outdir / "resume.pdf"
    output_png = outdir / "resume.png"
    output_jpg = outdir / "resume.jpg"
    output_markdown = outdir / input_path.name
    long_pdf = tmp_dir / "resume_long.pdf"

    register_fonts()
    outdir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    markdown = input_path.read_text(encoding="utf-8")
    shutil.copy2(input_path, output_markdown)
    parts = parse_resume(markdown)

    base_layout = resolve_layout_options(args)
    layouts = build_fit_layouts(base_layout) if args.fit_pages else [base_layout]
    selected_layout = layouts[-1]
    page_count = 0
    for layout in layouts:
        apply_layout(layout)
        build_pdf(build_story(parts), output_pdf, pagesize=A4)
        page_count = count_pdf_pages(output_pdf)
        selected_layout = layout
        if not args.fit_pages or page_count <= args.fit_pages:
            break

    apply_layout(selected_layout)

    long_height = story_height(build_story(parts))
    try:
        build_pdf(build_story(parts), long_pdf, pagesize=(PAGE_WIDTH, long_height))
        render_png_from_pdf(long_pdf, output_png, tmp_dir)
        render_jpg_from_png(output_png, output_jpg)
    finally:
        for tmp_file in (long_pdf, tmp_dir / "resume_png.png"):
            try:
                tmp_file.unlink()
            except FileNotFoundError:
                pass

    print(f"ReportLab input Markdown {input_path}")
    print(f"ReportLab saved Markdown {output_markdown}")
    print(f"ReportLab rendered PDF  {display_path(output_pdf)}")
    print(f"ReportLab rendered PNG  {display_path(output_png)}")
    print(f"ReportLab rendered JPG  {display_path(output_jpg)}")
    target_status = ""
    if args.fit_pages:
        met = "target met" if page_count <= args.fit_pages else "target not met"
        target_status = f", target={args.fit_pages} ({met})"
    print(
        f"ReportLab layout {selected_layout['name']}: pages={page_count}, "
        f"marginY={selected_layout['margin_y']}mm, lineHeight={selected_layout['line_height']}"
        f"{target_status}"
    )


if __name__ == "__main__":
    main()
