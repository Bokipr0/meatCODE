#!/usr/bin/env python3
"""Two-page PDF of the MeatCODE journal / publisher-access map."""
from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, KeepTogether)

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "reports"
OUT.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("jar", REPO / "pipeline" / "journal_access_report.py")
jar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jar)

D = jar.build()
TOTAL = D["total"]
STAMP = datetime.now(timezone.utc)
TAG = STAMP.strftime("%Y%m%d_%H%M")

H_WINE, H_PAID, H_FREE, H_GREY, H_CHECK, H_INK = (
    "#6B2340", "#C0392B", "#1E8449", "#6B6B6B", "#B7791F", "#1F1F1F")
WINE = colors.HexColor(H_WINE)
WINE_L = colors.HexColor("#F2E6EA")
PAID = colors.HexColor(H_PAID)
FREE = colors.HexColor(H_FREE)
GREY = colors.HexColor(H_GREY)
LINE = colors.HexColor("#D9D9D9")

S = ParagraphStyle("body", fontName="Helvetica", fontSize=8.4, leading=11, textColor=colors.HexColor("#1F1F1F"))
S_SM = ParagraphStyle("sm", parent=S, fontSize=7.2, leading=9.2, textColor=GREY)
S_H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=18, leading=21, textColor=WINE, spaceAfter=2)
S_H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=WINE,
                      spaceBefore=9, spaceAfter=4)
S_SUB = ParagraphStyle("sub", parent=S, fontSize=9, leading=12, textColor=GREY)
S_TH = ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=7.6, leading=9.4, textColor=colors.white)
S_TD = ParagraphStyle("td", fontName="Helvetica", fontSize=7.6, leading=9.4)
S_TDB = ParagraphStyle("tdb", parent=S_TD, fontName="Helvetica-Bold")

acc = {a["access"]: a for a in D["access_rows"]}
n_paid = acc.get("SUB", {}).get("n", 0)
n_free = acc.get("OA", {}).get("n", 0) + acc.get("PRE", {}).get("n", 0)
n_check = acc.get("MIX", {}).get("n", 0) + acc.get("UNK", {}).get("n", 0)
sd = next(p for p in D["platforms"] if p["platform"] == "ScienceDirect")

story = []

# ------------------------------------------------------------------ header
story.append(Paragraph("MeatCODE — journal &amp; publisher access map", S_H1))
story.append(Paragraph(
    "Where the literature corpus actually lives, and what it costs to read it. "
    f"All {TOTAL} sources in the Neon database, grouped by journal and by the platform the DOI resolves to.", S_SUB))
story.append(Paragraph(
    f"Generated {STAMP:%d %b %Y %H:%M} UTC &nbsp;·&nbsp; {TOTAL} sources &nbsp;·&nbsp; "
    f"{len(D['journals'])} distinct journals after name normalisation &nbsp;·&nbsp; read-only snapshot", S_SM))
story.append(Spacer(1, 7))

# ------------------------------------------------------------------- KPIs
S_KPI_N = ParagraphStyle("kpin", fontName="Helvetica-Bold", fontSize=19, leading=21)
S_KPI_L = ParagraphStyle("kpil", fontName="Helvetica", fontSize=7.4, leading=9.4,
                         textColor=GREY, spaceBefore=1)


def kpi(v, label, colour):
    """A list of flowables, not one Paragraph with <br/>: reportlab measures a
    mixed-font-size line by the SMALL font's leading, which clips the caption."""
    return [Paragraph(f'<font color="{colour}">{v}</font>', S_KPI_N),
            Paragraph(label, S_KPI_L)]


kpi_tbl = Table([[
    kpi(TOTAL, "sources in corpus", H_INK),
    kpi(n_paid, f"need a PAID subscription · {n_paid/TOTAL:.0%}", H_PAID),
    kpi(n_free, f"free to read, open access · {n_free/TOTAL:.0%}", H_FREE),
    kpi(sd["n"], f"sit on ScienceDirect · {sd['n']/TOTAL:.0%}", H_WINE)]],
    colWidths=[44*mm]*4)
kpi_tbl.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("BACKGROUND", (0, 0), (-1, -1), WINE_L),
    ("BOX", (0, 0), (-1, -1), 0.5, LINE),
    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
    ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
]))
story.append(kpi_tbl)
story.append(Spacer(1, 4))
story.append(Paragraph(
    f"<b>The one-line answer:</b> {sd['n']} of your {TOTAL} sources ({sd['n']/TOTAL:.0%}) are on ScienceDirect — "
    f"but only {sd['paid']} of those actually need a paid Elsevier subscription; the other "
    f"{sd['n']-sd['paid']} are gold open-access titles hosted there for free. "
    f"Across the whole corpus {n_paid} sources ({n_paid/TOTAL:.0%}) are paywalled.", S))

# ------------------------------------------------------- access split table
story.append(Paragraph("Access requirement", S_H2))
MEAN = {"SUB": "Needs an institutional subscription or per-article purchase",
        "OA": "Free to read for anyone, no login",
        "MIX": "Depends on the individual article — check before assuming",
        "PRE": "Free preprint — not peer reviewed",
        "UNK": "No DOI stored, so access could not be determined"}
rows = [[Paragraph("Access type", S_TH), Paragraph("Sources", S_TH),
         Paragraph("% of corpus", S_TH), Paragraph("What it means", S_TH)]]
for a in D["access_rows"]:
    col = H_PAID if a["access"] == "SUB" else H_FREE if a["access"] in ("OA", "PRE") else H_GREY
    rows.append([
        Paragraph(f'<font color="{col}"><b>{a["access_label"]}</b></font>', S_TD),
        Paragraph(str(a["n"]), S_TDB), Paragraph(f'{a["pct"]:.1f}%', S_TD),
        Paragraph(MEAN[a["access"]], S_TD)])
rows.append([Paragraph("<b>TOTAL</b>", S_TD), Paragraph(f"<b>{TOTAL}</b>", S_TD),
             Paragraph("<b>100.0%</b>", S_TD), Paragraph("", S_TD)])
t = Table(rows, colWidths=[38*mm, 17*mm, 20*mm, 101*mm], repeatRows=1)
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), WINE),
    ("BACKGROUND", (0, -1), (-1, -1), WINE_L),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
]))
story.append(t)

# ------------------------------------------------------------ platform table
story.append(Paragraph("Platform — where you have to go, and how many articles are waiting there", S_H2))
rows = [[Paragraph("Platform / gateway", S_TH), Paragraph("Publisher (CrossRef registrant)", S_TH),
         Paragraph("Total", S_TH), Paragraph("% corpus", S_TH), Paragraph("Paid", S_TH),
         Paragraph("Free", S_TH), Paragraph("Journals", S_TH)]]
shown = [p for p in D["platforms"] if p["n"] >= 2]
other = [p for p in D["platforms"] if p["n"] < 2]
for p in shown:
    free = p["free"] + p["other"]
    rows.append([
        Paragraph(f'<b>{p["platform"]}</b>', S_TD),
        Paragraph(p["publisher"][:44], S_TD),
        Paragraph(str(p["n"]), S_TDB),
        Paragraph(f'{p["pct"]:.1f}%', S_TD),
        Paragraph(f'<font color="#C0392B"><b>{p["paid"] or "—"}</b></font>', S_TD),
        Paragraph(f'<font color="#1E8449">{free or "—"}</font>', S_TD),
        Paragraph(str(p["journals"]), S_TD)])
if other:
    rows.append([Paragraph(f'<i>{len(other)} further platforms, 1 source each</i>', S_TD),
                 Paragraph("<i>various society / regional publishers</i>", S_TD),
                 Paragraph(str(sum(p["n"] for p in other)), S_TD),
                 Paragraph(f'{sum(p["n"] for p in other)/TOTAL:.1f}%', S_TD),
                 Paragraph(f'<font color="#C0392B">{sum(p["paid"] for p in other) or "—"}</font>', S_TD),
                 Paragraph(f'<font color="#1E8449">{sum(p["free"]+p["other"] for p in other) or "—"}</font>', S_TD),
                 Paragraph(str(sum(p["journals"] for p in other)), S_TD)])
rows.append([Paragraph("<b>TOTAL</b>", S_TD), Paragraph("", S_TD), Paragraph(f"<b>{TOTAL}</b>", S_TD),
             Paragraph("<b>100.0%</b>", S_TD),
             Paragraph(f'<b><font color="#C0392B">{sum(p["paid"] for p in D["platforms"])}</font></b>', S_TD),
             Paragraph(f'<b><font color="#1E8449">{sum(p["free"]+p["other"] for p in D["platforms"])}</font></b>', S_TD),
             Paragraph(f'<b>{len(D["journals"])}</b>', S_TD)])
t = Table(rows, colWidths=[40*mm, 60*mm, 14*mm, 17*mm, 14*mm, 14*mm, 17*mm], repeatRows=1)
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), WINE),
    ("BACKGROUND", (0, -1), (-1, -1), WINE_L),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ALIGN", (2, 0), (-1, -1), "CENTER"),
    ("TOPPADDING", (0, 0), (-1, -1), 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#FAFAFA")]),
]))
story.append(t)
story.append(Spacer(1, 3))
story.append(Paragraph(
    "A platform can carry both paid and free titles — ScienceDirect hosts <i>Food Chemistry</i> (paywalled) and "
    "<i>Food Chemistry: X</i> (gold open access), so the Paid / Free columns split each platform rather than "
    "labelling the whole gateway one way.", S_SM))

story.append(PageBreak())

# ============================================================== PAGE 2
story.append(Paragraph("Top 32 journals by number of sources", S_H1))
story.append(Paragraph(
    "Scan the <b>Paid?</b> column. The full 170-journal list, the merged name variants and the "
    "verification basis for each access call are in the accompanying .xlsx.", S_SUB))
story.append(Spacer(1, 6))

rows = [[Paragraph("#", S_TH), Paragraph("Journal", S_TH), Paragraph("Sources", S_TH),
         Paragraph("% corpus", S_TH), Paragraph("Paid?", S_TH), Paragraph("Platform / gateway", S_TH)]]
TOPN = 32
for n, j in enumerate(D["journals"][:TOPN], start=1):
    pf = {"SUB": ("PAID", "#C0392B"), "OA": ("FREE", "#1E8449"), "PRE": ("FREE", "#1E8449"),
          "MIX": ("CHECK", "#B7791F"), "UNK": ("CHECK", "#B7791F")}[j["access"]]
    rows.append([
        Paragraph(str(n), S_TD),
        Paragraph(j["journal"][:58], S_TDB if j["n"] >= 10 else S_TD),
        Paragraph(str(j["n"]), S_TDB),
        Paragraph(f'{j["pct"]:.1f}%', S_TD),
        Paragraph(f'<font color="{pf[1]}"><b>{pf[0]}</b></font>', S_TD),
        Paragraph(j["platform"], S_TD)])
shown_n = sum(j["n"] for j in D["journals"][:TOPN])
rows.append([Paragraph("", S_TD), Paragraph(f"<b>Top {TOPN} subtotal</b>", S_TD),
             Paragraph(f"<b>{shown_n}</b>", S_TD), Paragraph(f"<b>{shown_n/TOTAL:.1%}</b>", S_TD),
             Paragraph("", S_TD),
             Paragraph(f'<i>remaining {len(D["journals"])-TOPN} journals: {TOTAL-shown_n} sources</i>', S_TD)])
t = Table(rows, colWidths=[8*mm, 78*mm, 16*mm, 18*mm, 16*mm, 40*mm], repeatRows=1)
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), WINE),
    ("BACKGROUND", (0, -1), (-1, -1), WINE_L),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ALIGN", (2, 0), (4, -1), "CENTER"), ("ALIGN", (0, 0), (0, -1), "CENTER"),
    ("TOPPADDING", (0, 0), (-1, -1), 2.1), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.1),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#FAFAFA")]),
]))
story.append(t)

story.append(Paragraph("Method &amp; caveats", S_H2))
n_unk = acc.get("UNK", {}).get("n", 0)
notes = [
    ("Names were normalised first.", "The raw table holds 213 distinct journal strings for only "
     f"{len(D['journals'])} real journals. 'Food Chemistry' / 'Food chemistry', 'Foods' / "
     "'Foods (Basel, Switzerland)' and 'Food chemistry: X' / 'Food Chemistry X' were each merged. "
     "Counting the raw strings would have split the biggest journals in two."),
    ("Publishers come from the DOI prefix, not the journal name.", "All 39 distinct prefixes in the corpus "
     "were resolved against the CrossRef API (api.crossref.org/prefixes/) on 5 Aug 2026. Attribution is applied "
     "per journal using that journal's dominant prefix, so a row missing its own DOI still inherits the right "
     "platform — which is why ScienceDirect shows 349 while only 334 rows literally carry a 10.1016 DOI."),
    ("Open vs paid was verified, not assumed.", "Every journal with 4+ sources was checked individually "
     "against OpenAlex (is_oa, is_in_doaj) and DOAJ. That check moved 118 ScienceDirect sources from "
     "'paid' to 'free'. Smaller journals fall back to the publisher default and are flagged as such "
     "in the spreadsheet."),
    ("Three things this does not tell you.", "49 sources have no DOI; 24 inherit their journal's status, the "
     f"other {n_unk} are in journals where no row has a DOI at all (Food Hydrocolloids, LWT, Trends in Food "
     "Science &amp; Technology and 18 more) and are reported as Unknown rather than guessed. 'Hybrid' journals "
     "vary article by article and would need an Unpaywall lookup per DOI. And a journal being open access "
     "today does not free its back catalogue — Poultry Science and Journal of Dairy Science only went gold "
     "OA in 2020 and 2024."),
    ("One unresolved conflict.", "Food Science &amp; Nutrition (ISSN 2048-7177, 8 sources): Wiley lists it as "
     "open access, OpenAlex reports is_oa = false. Left as 'Hybrid' rather than guessing."),
]
for head, body in notes:
    story.append(Paragraph(f"<b>{head}</b> {body}", S_SM))
    story.append(Spacer(1, 2.2))

story.append(Spacer(1, 4))
story.append(Paragraph(
    "Read-only: nothing was written to the database. Reproduce with "
    "<font face='Courier'>python3 pipeline/build_journal_report.py</font> and "
    "<font face='Courier'>python3 pipeline/build_journal_pdf.py</font>.", S_SM))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(15*mm, 13*mm, A4[0]-15*mm, 13*mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GREY)
    canvas.drawString(15*mm, 8.5*mm, f"MeatCODE — journal & publisher access map · {STAMP:%d %b %Y}")
    canvas.drawRightString(A4[0]-15*mm, 8.5*mm, f"Page {doc.page} of 2")
    canvas.restoreState()


pdf_path = OUT / f"meatcode_journal_access_{TAG}.pdf"
doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                        leftMargin=15*mm, rightMargin=15*mm,
                        topMargin=13*mm, bottomMargin=18*mm,
                        title="MeatCODE — journal & publisher access map",
                        author="MeatCODE")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("pdf:", pdf_path)
