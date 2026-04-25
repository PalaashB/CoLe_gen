"""
Professional PDF cover letter generator using ReportLab.
Uses only built-in fonts (Helvetica family) — no external font files needed.
"""

import re
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter as LETTER_SIZE
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from config.settings import APPLICATIONS_DIR


class PDFGenerator:
    """Create professional PDF cover letters."""

    def generate(
        self,
        letter_text: str,
        user_profile: dict,
        job_data: dict,
        output_dir: str | Path | None = None,
    ) -> str:
        """Build a PDF and return the full path to the saved file."""
        out = Path(output_dir) if output_dir else APPLICATIONS_DIR
        out.mkdir(parents=True, exist_ok=True)

        filename = self._make_filename(job_data)
        filepath = out / filename

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=LETTER_SIZE,
            leftMargin=1 * inch,
            rightMargin=1 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
        )

        styles = self._build_styles()
        story = self._build_story(letter_text, user_profile, job_data, styles)

        doc.build(story)
        return str(filepath)

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------
    @staticmethod
    def _build_styles() -> dict:
        base = getSampleStyleSheet()
        return {
            "name": ParagraphStyle(
                "Name",
                parent=base["Normal"],
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=20,
                spaceAfter=2,
            ),
            "contact": ParagraphStyle(
                "Contact",
                parent=base["Normal"],
                fontName="Helvetica",
                fontSize=10,
                leading=14,
                textColor="#444444",
                spaceAfter=0,
            ),
            "date": ParagraphStyle(
                "Date",
                parent=base["Normal"],
                fontName="Helvetica",
                fontSize=11,
                leading=14,
                spaceAfter=4,
            ),
            "recipient": ParagraphStyle(
                "Recipient",
                parent=base["Normal"],
                fontName="Helvetica",
                fontSize=11,
                leading=14,
                spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "Body",
                parent=base["Normal"],
                fontName="Helvetica",
                fontSize=11,
                leading=12.65,  # ~1.15 line spacing
                spaceAfter=8,
                alignment=4,  # justified
            ),
            "closing": ParagraphStyle(
                "Closing",
                parent=base["Normal"],
                fontName="Helvetica",
                fontSize=11,
                leading=14,
                spaceBefore=12,
            ),
            "signature": ParagraphStyle(
                "Signature",
                parent=base["Normal"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=14,
            ),
        }

    # ------------------------------------------------------------------
    # Story (content flow)
    # ------------------------------------------------------------------
    def _build_story(
        self,
        letter_text: str,
        user_profile: dict,
        job_data: dict,
        styles: dict,
    ) -> list:
        story = []
        personal = user_profile.get("personal_info", {})

        # --- Header: name ---
        name = personal.get("name", "")
        if name:
            story.append(Paragraph(name, styles["name"]))

        # --- Contact line 1: email | phone | location ---
        contact_parts = []
        for field in ("email", "phone", "location"):
            val = personal.get(field, "")
            if val:
                contact_parts.append(val)
        if contact_parts:
            story.append(Paragraph(" &nbsp;|&nbsp; ".join(contact_parts), styles["contact"]))

        # --- Contact line 2: linkedin | github | portfolio ---
        link_parts = []
        for field in ("linkedin", "github", "portfolio"):
            val = personal.get(field, "")
            if val:
                link_parts.append(val)
        if link_parts:
            story.append(Paragraph(" &nbsp;|&nbsp; ".join(link_parts), styles["contact"]))

        story.append(Spacer(1, 20))

        # --- Date ---
        today = datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(today, styles["date"]))

        story.append(Spacer(1, 12))

        # --- Recipient ---
        company = job_data.get("company_name", "")
        position = job_data.get("position_title", "")
        if company:
            story.append(Paragraph(company, styles["recipient"]))
        if position:
            story.append(Paragraph(position, styles["recipient"]))

        story.append(Spacer(1, 12))

        # --- Letter body ---
        # Split the letter into paragraphs; skip "Sincerely," lines (handled below)
        body, closing_name = self._split_letter(letter_text, name)
        for para in body:
            para_clean = para.strip()
            if para_clean:
                # Escape XML-unsafe characters for ReportLab
                para_clean = para_clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(para_clean, styles["body"]))

        story.append(Spacer(1, 20))

        # --- Closing ---
        story.append(Paragraph("Sincerely,", styles["closing"]))
        story.append(Spacer(1, 4))
        sign_name = closing_name or name
        if sign_name:
            story.append(Paragraph(sign_name, styles["signature"]))

        return story

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _split_letter(letter_text: str, default_name: str) -> tuple[list[str], str]:
        """Split letter into body paragraphs and extract the signature name."""
        lines = letter_text.strip().split("\n")
        body_lines: list[str] = []
        closing_name = ""
        skip_rest = False

        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("sincerely"):
                skip_rest = True
                continue
            if skip_rest:
                if stripped:
                    closing_name = stripped.rstrip(",").strip()
                continue
            body_lines.append(line)

        # Group into paragraphs by blank lines
        text = "\n".join(body_lines).strip()
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

        return paragraphs, closing_name or default_name

    @staticmethod
    def _make_filename(job_data: dict) -> str:
        """Generate a sanitised filename."""
        company = job_data.get("company_name", "Company")
        position = job_data.get("position_title", "Position")
        date_str = datetime.now().strftime("%Y-%m-%d")

        safe = re.sub(r"[^\w\s-]", "", f"{company}_{position}".replace(" ", ""))
        safe = re.sub(r"[-\s]+", "_", safe).strip("_")

        return f"{safe}_{date_str}.pdf"
