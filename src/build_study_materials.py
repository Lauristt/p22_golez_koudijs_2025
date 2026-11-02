"""Build original study notes and local-only screenshots from a version-locked paper."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
from xml.sax.saxutils import escape

import pymupdf
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "paper breakdown"
OUTPUT = ROOT / "output" / "pdf"
PAPER = NOTES / "source" / "GolezKoudijs2025EquityDurationPredictability.pdf"
BLUE = colors.HexColor("#16324F")
GRAY = colors.HexColor("#536273")
STYLES = getSampleStyleSheet()
BODY = ParagraphStyle("Body", parent=STYLES["BodyText"], fontSize=10.3, leading=14.6, textColor=BLUE)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8, leading=11, textColor=GRAY)


def manifest():
    """Read the source version and manually verified exhibit bounds."""
    return json.loads((NOTES / "exhibits.json").read_text())


def verify_paper(data, expected):
    """Reject HTML responses and changed source versions before extracting exhibits."""
    if not data.startswith(b"%PDF-"):
        raise ValueError("The source did not return a PDF.")
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Paper checksum changed. Review the version before updating the manifest.")


def fetch_paper():
    """Download the exact course-linked paper, or verify the existing local copy."""
    meta = manifest()
    if PAPER.exists():
        verify_paper(PAPER.read_bytes(), meta["sha256"])
        return
    with urlopen(meta["source_url"], timeout=60) as response:
        data = response.read()
    verify_paper(data, meta["sha256"])
    PAPER.parent.mkdir(parents=True, exist_ok=True)
    temporary = PAPER.with_suffix(".tmp")
    temporary.write_bytes(data)
    temporary.replace(PAPER)


def paragraph(c, text, x, top, width, style=BODY):
    """Draw wrapped text and return the next usable vertical coordinate."""
    item = Paragraph(text, style)
    _, height = item.wrap(width, 720)
    if top - height < 48:
        raise ValueError("PDF text would overlap the footer; adjust the page layout.")
    item.drawOn(c, x, top - height)
    return top - height


def header(c, label, number, title):
    """Draw consistent document furniture on an A4-like letter-sized page."""
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(48, 750, "P22  /  EQUITY DURATION AND PREDICTABILITY")
    c.setStrokeColor(colors.HexColor("#CBD5DF"))
    c.line(48, 738, 564, 738)
    y = paragraph(c, escape(title), 48, 714, 516, ParagraphStyle("Title", parent=BODY, fontSize=23, leading=28))
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    c.drawString(48, 29, label)
    c.drawRightString(564, 29, str(number))
    return y - 22


def make_walkthrough():
    """Render six original explanatory pages, with explicit source and status notes."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pages = json.loads((NOTES / "walkthrough.json").read_text())
    c = canvas.Canvas(str(OUTPUT / "paper_walkthrough.pdf"), pagesize=(612, 792))
    c.setTitle("P22 - Paper walkthrough")
    c.setAuthor("Lauris Li")
    for i, page in enumerate(pages, 1):
        y = header(c, "Lauris Li | Study guide | Source: Golez & Koudijs (2025), JFE 172, 104114", i, page["title"])
        for block in page["blocks"]:
            y = paragraph(c, "<b>" + escape(block["heading"]) + "</b>", 48, y, 516) - 5
            y = paragraph(c, escape(block["text"]), 48, y, 516) - 17
        c.showPage()
    c.save()


def make_packet():
    """Render eight original exhibit crops with full captions into a reply attachment."""
    fetch_paper()
    meta = manifest()
    screenshots = NOTES / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUTPUT / "answer_question.pdf"), pagesize=(612, 792))
    c.setTitle("P22 - Assigned exhibit confirmation")
    c.setAuthor("Lauris Li")
    y = header(c, "Lauris Li | Draft attachment for Jeremy | Not sent", 1, "Assigned exhibit confirmation")
    intro = [
        "Hi Jeremy,",
        'We are using the published copy of Golez and Koudijs, "Equity duration and predictability," linked in the course project description. The following eight screenshots preserve the original exhibits and their captions/notes. They are reference images, not our replicated results.',
        "<b>Source:</b> Journal of Financial Economics 172 (2025), article 104114.<br/>DOI: 10.1016/j.jfineco.2025.104114",
        "<b>Assigned exhibits:</b> Table 1 (p. 4), Table 2 (p. 5), Table 4 (p. 7), Figure 1, both panels (p. 8), Table 5 (p. 9), Tables 6 and 7 (p. 10), and Figure 3 (p. 11). Tables 8 and 9 are excluded.",
        "<b>Version questions:</b> The assignment lists volume 171, while this PDF says 172. Table 5 has three columns (1945-2022, 1629-1945, and the full sample), while the task description mentions four historical subperiods. Figure 1's caption mentions 2017 in one sentence despite its 2022 title and plotted endpoint. Could you confirm that these are the intended exhibits?",
        "Best,<br/>Lauris Li<br/>On behalf of Yuting Li, Yiyao Wang, Gary Miao, and Luke Zhu",
    ]
    for item in intro:
        y = paragraph(c, item, 48, y, 516) - 17
    y = paragraph(c, '<link href="' + meta["source_url"] + '">Source: course-linked paper PDF (click to open)</link>', 48, y, 516, SMALL) - 10
    paragraph(c, "Version SHA-256:<br/>" + meta["sha256"][:32] + "<br/>" + meta["sha256"][32:], 48, y, 516, SMALL)
    c.showPage()
    with pymupdf.open(PAPER) as paper:
        for i, exhibit in enumerate(meta["exhibits"], 2):
            page = paper[exhibit["page"] - 1]
            bounds = pymupdf.Rect(exhibit["crop"])
            if not page.rect.contains(bounds):
                raise ValueError("Exhibit crop is outside the paper page.")
            label = exhibit["label"].replace("Figure", "Fig.")
            if label not in page.get_text("text", clip=bounds):
                raise ValueError(f"Missing exhibit label in crop: {label}")
            path = screenshots / (exhibit["id"] + ".png")
            page.get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=bounds, alpha=False).save(path)
            top = header(c, "Original paper excerpt | Golez & Koudijs (2025) | Local reference only", i, exhibit["label"] + " | Paper page " + str(exhibit["page"]))
            top = paragraph(c, escape(exhibit["title"]), 48, top, 516, SMALL) - 16
            width, height = bounds.width, bounds.height
            scale = min(516 / width, (top - 68) / height)
            draw_w, draw_h = width * scale, height * scale
            c.drawImage(ImageReader(str(path)), 48 + (516 - draw_w) / 2, top - draw_h, draw_w, draw_h)
            c.showPage()
    c.save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["walkthrough", "packet"])
    args = parser.parse_args()
    if args.mode == "walkthrough":
        make_walkthrough()
    else:
        make_packet()
