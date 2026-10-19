"""
Assemble the full manuscript: the Abstract, then the revised Introduction
taken from the Word file, followed by the Methods, Results and Discussion
drafts, with one reference list.

    python _merge_manuscript.py OUT.docx

The Introduction exists only as a .docx, so its paragraphs, its two tables and
its reference list are read back out of that file. The later sections are read
from Markdown. A single reference list is assembled from the Introduction's
numbering, to which those sections already conform, with any citation appearing
only in the later sections appended.

Editorial notes marked in the Markdown drafts are dropped; they exist for the
authors and not for the journal.
"""

import csv
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
INTRO_DOCX = HERE / "Manuscript_Introduction_and_Literature_revised.docx"
METHODS_MD = HERE / "02_METHODS.md"
ABSTRACT_MD = HERE / "00_ABSTRACT.md"
RESULTS_MD = HERE / "03_RESULTS.md"
DISCUSSION_MD = HERE / "04_DISCUSSION.md"

FONT, BODY_PT, TABLE_PT = "Times New Roman", 12, 9

FIG_DIR = HERE.parent / "04_results" / "figures"
TBL_DIR = HERE.parent / "04_results" / "tables"

# Captions are held to twenty words. Anything longer belongs in the text or in
# the annotation drawn inside the figure itself.
FIGURES = {
    "Fig1": ("Fig1_methodology_workflow.png",
             "Figure 1. Data and analysis workflow from the published survey "
             "through cleaning and preprocessing to the reported tables."),
    "Fig2": ("Fig2_analysis_architecture.png",
             "Figure 3. Analysis architecture, showing the predictor tiers, "
             "the three validation schemes and the quantities reported."),
    "Fig3": ("Fig3_study_area.png",
             "Figure 2. Study area showing development wells in four special "
             "study areas and external wells across North Bengal."),
    "Fig4": ("Fig4_feasibility_matrix.png",
             "Figure 4. Predictive skill by metal and cost tier, mean R² over "
             "twenty five random outer folds."),
    "Fig5": ("Fig5_validation_comparison.png",
             "Figure 5. How much skill survives honest validation: random "
             "folds against spatial blocks, and transfer to unseen districts."),
    "Fig6": ("Fig6_conformal_coverage.png",
             "Figure 6. Conformal interval coverage within the study area and "
             "under transfer to external wells."),
    "Fig7": ("Fig7_roc_operating_points.png",
             "Figure 11. Arsenic screening performance on external wells and "
             "operating points against the Bangladesh standard."),
    "Fig8": ("Fig8_redox_arsenic.png",
             "Figure 8. Arsenic concentration and guideline exceedance follow "
             "redox condition across the zonation."),
    "Fig9": ("Fig9_feature_importance.png",
             "Figure 7. Permutation importance showing what each model "
             "actually uses, with redox indicators marked."),
    "Fig11": ("Fig11_learning_curves.png",
              "Figure 10. Learning curves for the four spatially robust "
              "metals, held-out R² against training set size."),
    "Fig13": ("Fig13_district_iron_auc.png",
              "Figure 12. Iron ranks arsenic differently in each external "
              "district, against its value in the development set."),
    "Fig12": ("Fig12_geology_arsenic.png",
              "Figure 9. Arsenic by surface geology in the national survey, "
              "which includes the external test wells."),
}

TABLES = {
    "T0": ("T0_descriptive_statistics.csv",
           "Table 4. Descriptive statistics for all predictors, targets and "
           "geochemistry, with censoring and detection limits."),
    "T0b": ("T0b_exceedance_summary.csv",
            "Table 6. Guideline exceedance summary for the thirteen trace "
            "metals against WHO and Bangladesh standards."),
    "T1": ("T1_target_screening.csv",
           "Table 7. Screening of the thirteen candidate targets, with the "
           "reason each excluded metal was dropped."),
    "T2": ("T2_feasibility_matrix.csv",
           "Table 8. Feasibility matrix of every target and tier under random "
           "cross validation, with the dominant model family."),
    "T3": ("T3_conformal_coverage.csv",
           "Table 11. Held-out split conformal coverage and interval width for "
           "each feasible target and tier."),
    "T4": ("T4_censoring_comparison.csv",
           "Table 12. Comparison of four censoring treatments on identical "
           "folds, with the resulting spread in R²."),
    "T5": ("T5_external_validation.csv",
           "Table 10. External validation on unseen North Bengal districts, "
           "with conformal coverage under transfer."),
    "T6": ("T6_charge_balance.csv",
           "Table 3. Charge balance error statistics for the analytical "
           "quality check."),
    "T7": ("T7_redox_zonation.csv",
           "Table 14. Redox zonation after McMahon and Chapelle, with arsenic, "
           "iron and manganese by zone."),
    "T8": ("T8_water_types.csv",
           "Table 5. Hydrochemical water types by Piper classification, with "
           "well counts and median arsenic."),
    "T9": ("T9_spatial_vs_random_cv.csv",
           "Table 9. Random against spatially blocked cross validation for "
           "every target, tier and block count."),
    "T19": ("T19_baseline_comparison.csv",
            "Table 19. Raw iron against the fitted model on the external "
            "wells, with the development comparison and kit degradation."),
    "T10": ("T10_operating_points.csv",
            "Table 18. Operating points for arsenic screening on external "
            "wells under both regulatory standards."),
    "T11": ("T11_depth_strata.csv",
            "Table 16. Arsenic and iron by depth stratum, showing where the "
            "two decouple."),
    "T12": ("T12_feature_importance.csv",
            "Table 13. Permutation feature importance for every modelled "
            "metal, with redox indicators flagged."),
    "T13": ("T13_learning_curve.csv",
            "Table 17. Learning curve results, held-out R² against training "
            "set size for four metals."),
    "T14": ("T14_geology_arsenic.csv",
            "Table 15. Arsenic by surface geology unit in the national "
            "survey, with exceedance percentages."),
}


# The Introduction's closing sentence was drafted before the final results and
# asserts that the metals which can be screened are not the hazardous ones.
# The completed analysis contradicts that: arsenic and uranium both exceed
# their guidelines and both survive spatial validation. The sentence is
# replaced here so the Introduction and Results do not disagree.
HEADLINE_OLD = ("The principal finding is that surrogate screening is feasible "
                "for a minority of trace metals, that the metals for which it "
                "succeeds are not those posing the greatest health risk in this "
                "setting, and that conformal intervals which are well calibrated "
                "within the study area lose their validity in an unpredictable "
                "manner upon transfer.")
HEADLINE_NEW = ("The principal finding is that surrogate screening is feasible "
                "for a minority of trace metals; that the detection limit sets "
                "a ceiling on which metals can be modelled at all, while below "
                "that ceiling feasibility is decided by whether the field "
                "measurable predictors carry information about the metal; and "
                "that what transfers to unseen districts is the ranking of "
                "wells by risk rather than their concentrations, while "
                "conformal intervals that are well calibrated within the study "
                "area lose their validity in an unpredictable manner upon "
                "transfer.")

# The Introduction captions Table 1 but leaves its summary table unlabelled.
TABLE2_CAPTION = ("Table 2. Summary of practices across the thirteen reviewed "
                  "studies, counted from Table 1.")

# Cited in Methods but absent from the Introduction's list.
EXTRA_REFS = {
    64: ("Benjamini Y, Hochberg Y (1995) Controlling the false discovery rate: "
         "a practical and powerful approach to multiple testing. Journal of the "
         "Royal Statistical Society Series B 57(1):289-300. "
         "https://doi.org/10.1111/j.2517-6161.1995.tb02031.x"),
    # Prior art for the iron result. Added after stage 3.15; the heuristic is
    # established and the paper must not claim it.
    65: ("Annaduzzaman M, Bhattacharya P, Biswas A, Hossain M, Ahmed KM, "
         "van Halem D (2018) Arsenic and manganese in shallow tubewells: "
         "validation of platform color as a screening tool in Bangladesh. "
         "Groundwater for Sustainable Development 6:181-188. "
         "https://doi.org/10.1016/j.gsd.2017.11.008"),
    66: ("Chatterjee R, Mal U, et al. Tube well platform colour as a proxy for "
         "identification of arsenic contaminated wells: case study from "
         "alluvial aquifers of eastern India. International Journal of "
         "Environmental Analytical Chemistry. "
         "[NEW: year, volume, pages and DOI from the journal page]"),
    67: ("University of Portsmouth (2025) iArsenic: mobile and web tool for "
         "arsenic risk assessment in tubewell water (bilingual: Bengali and "
         "English), v1 [web application]. University of Portsmouth, "
         "Portsmouth. https://researchportal.port.ac.uk/en/publications/"
         "iarsenic-mobile-and-web-tool-for-arsenic-risk-assessment-in-tubew/"),
    68: ("Hoque MA, Butler AP (2016) Can water quality of tubewells be "
         "assessed without chemical testing? Geophysical Research Abstracts "
         "18:EGU2016-15455."),
    69: ("Horneman A, van Geen A, Kent DV, Mathe PE, Zheng Y, Dhar RK, "
         "O'Connell S, Hoque MA, Aziz Z, Shamsudduha M, Seddique AA, "
         "Ahmed KM (2004) Decoupling of As and Fe release to Bangladesh "
         "groundwater under reducing conditions. Part I: evidence from "
         "sediment profiles. Geochimica et Cosmochimica Acta 68(17):3459-3473. "
         "https://doi.org/10.1016/j.gca.2004.01.026"),
    70: ("Ohno K, Furukawa A, Hayashi K, Kamei T, Magara Y (2005) Arsenic "
         "contamination of groundwater in Nawabganj, Bangladesh, focusing on "
         "the relationship with other metals and ions. Water Science and "
         "Technology 52(8):87-94. [NEW: DOI from the IWA Publishing page]"),
    71: ("Hossain M, et al. (2014) Sediment colour tool for targeting arsenic "
         "safe aquifers for the installation of shallow drinking water "
         "tubewells. Science of the Total Environment. "
         "[NEW: full author list, year, volume, pages and DOI from PubMed "
         "24984232]"),
}


# ── reading ────────────────────────────────────────────────────────────────
def read_intro(path):
    """Return (body blocks, references) from the Introduction document."""
    doc = Document(path)
    body, refs, in_refs = [], {}, False
    t_index = 0
    tables = doc.tables

    for block in doc.element.body.iterchildren():
        if block.tag == qn("w:p"):
            para = next(p for p in doc.paragraphs if p._p is block)
            text = para.text.strip()
            if not text:
                continue
            if text.lower().startswith("reference"):
                in_refs = True
                continue
            m = re.match(r"^\[(\d+)\]\s*(.+)", text)
            if in_refs and m:
                refs[int(m.group(1))] = m.group(2).strip()
                continue
            if in_refs:
                continue
            style = para.style.name
            level = 1 if style == "Heading 1" else 2 if style == "Heading 2" else 0
            body.append(("heading", level, text) if level else ("para", 0, text))
        elif block.tag == qn("w:tbl"):
            if t_index < len(tables):
                rows = [[c.text.strip() for c in r.cells] for r in tables[t_index].rows]
                if t_index == 1:
                    body.append(("caption", 0, TABLE2_CAPTION))
                body.append(("table", 0, rows))
                t_index += 1
    return body, refs


def read_markdown(path):
    """Parse a drafted section into the same block form."""
    text = path.read_text(encoding="utf-8").split("## Notes for revision")[0]
    lines = text.split("\n")
    blocks, i = [], 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip() or line.strip() == "---" or line.lstrip().startswith(">"):
            i += 1
            continue
        if line.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                if not re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i]):
                    rows.append([c.strip() for c in
                                 lines[i].strip().strip("|").split("|")])
                i += 1
            blocks.append(("table", 0, rows))
            continue
        m = re.match(r"^\{\{TITLE:(.+)\}\}$", line.strip())
        if m:
            blocks.append(("title", 0, m.group(1).strip()))
            i += 1
            continue
        m = re.match(r"^\{\{(FIGURE|TABLE):([A-Za-z0-9_]+)\}\}$", line.strip())
        if m:
            blocks.append(("figure" if m.group(1) == "FIGURE" else "csv",
                           0, m.group(2)))
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            blocks.append(("heading", len(m.group(1)), m.group(2).strip()))
            i += 1
            continue
        chunk = []
        while (i < len(lines) and lines[i].strip()
               and not lines[i].lstrip().startswith(("|", ">"))
               and not re.match(r"^#{1,3}\s", lines[i])
               and lines[i].strip() != "---"):
            chunk.append(lines[i].strip())
            i += 1
        if chunk:
            blocks.append(("para", 0, " ".join(chunk)))
    return blocks


# ── writing ────────────────────────────────────────────────────────────────
def tight_margins(table, twips=40):
    """Default cell padding costs a wide table a third of the text column."""
    pr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side in ("left", "right"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(twips))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    pr.append(mar)


def shade(cell, colour):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:fill"), colour)
    cell._tc.get_or_add_tcPr().append(el)


def add_runs(paragraph, text):
    for part in re.split(r"(\*\*.+?\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Courier New"
            run.font.size = Pt(BODY_PT - 1)
        else:
            paragraph.add_run(part)


def write_table(doc, rows, size=TABLE_PT, avail=6.5):
    if not rows:
        return
    n_cols = len(rows[0])
    table = doc.add_table(rows=len(rows), cols=n_cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    if n_cols >= 9:
        tight_margins(table)

    longest = [max(len(r[c]) for r in rows if c < len(r)) for c in range(n_cols)]
    weights = [min(max(w, 6), 26) for w in longest]
    widths = [Inches(avail * w / sum(weights)) for w in weights]
    for c, width in enumerate(widths):
        for r in range(len(rows)):
            table.cell(r, c).width = width

    for r, row in enumerate(rows):
        for c, cell_text in enumerate(row[:n_cols]):
            cell = table.cell(r, c)
            cell.text = ""
            para = cell.paragraphs[0]
            para.paragraph_format.line_spacing = 1.0
            para.paragraph_format.space_after = Pt(2)
            add_runs(para, cell_text)
            for run in para.runs:
                run.font.size = Pt(size)
                run.font.name = FONT
                if r == 0:
                    run.bold = True
            if r == 0:
                shade(cell, "D9D9D9")
    doc.add_paragraph()


def add_caption(doc, text):
    """A caption sits tight under its figure or over its table."""
    para = doc.add_paragraph()
    para.paragraph_format.line_spacing = 1.0
    para.paragraph_format.space_after = Pt(10)
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = para.add_run(text)
    run.font.size = Pt(BODY_PT - 2)
    run.bold = True
    return para


def write_figure(doc, key):
    name, caption = FIGURES[key]
    path = FIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)

    # Fit to the text column, but never past the printable height, so a tall
    # portrait diagram does not push its own caption onto the next page.
    max_w, max_h = 6.5, 7.6
    width = max_w
    try:
        from PIL import Image
        with Image.open(path) as im:
            w_px, h_px = im.size
        if max_w * h_px / w_px > max_h:
            width = max_h * w_px / h_px
    except ImportError:
        pass

    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(4)
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.add_run().add_picture(str(path), width=Inches(width))
    add_caption(doc, caption)


def fmt(value):
    """Trim stored float noise for display without touching the stored data."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    if value.strip().lstrip("-").isdigit():
        return value
    return f"{number:.4g}"


def set_orientation(section, landscape):
    """Letter paper either way; the section break is what turns the page."""
    short, long_ = Inches(8.5), Inches(11)
    if landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = long_, short
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width, section.page_height = short, long_
    for margin in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, margin, Inches(1))


def write_csv_table(doc, key):
    name, caption = TABLES[key]
    path = TBL_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [[fmt(c) for c in row] for row in csv.reader(handle)]
    rows[0] = [c.replace("_", " ") for c in rows[0]]
    n_cols = len(rows[0])

    # Past twelve columns the text column cannot hold the table legibly, so it
    # is given a landscape page of its own and the text resumes in portrait.
    wide = n_cols >= 13
    if wide:
        set_orientation(doc.add_section(WD_SECTION.NEW_PAGE), landscape=True)

    add_caption(doc, caption)
    write_table(doc, rows,
                size=7.0 if wide else 7.5 if n_cols >= 9 else TABLE_PT,
                avail=9.0 if wide else 6.5)

    if wide:
        set_orientation(doc.add_section(WD_SECTION.NEW_PAGE), landscape=False)


def main():
    out = Path(sys.argv[1])

    abstract = read_markdown(ABSTRACT_MD)
    intro_blocks, refs = read_intro(INTRO_DOCX)
    methods = read_markdown(METHODS_MD)
    results = read_markdown(RESULTS_MD)
    discussion = read_markdown(DISCUSSION_MD)
    refs.update(EXTRA_REFS)

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(BODY_PT)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    pf = normal.paragraph_format
    pf.line_spacing, pf.space_after = 2.0, Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for section in doc.sections:
        section.page_width, section.page_height = Inches(8.5), Inches(11)
        for margin in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(section, margin, Inches(1))

    for level in (1, 2, 3):
        st = doc.styles[f"Heading {level}"]
        st.font.name = FONT
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.font.size = Pt(BODY_PT + (2 if level == 1 else 1 if level == 2 else 0))

    def emit(blocks):
        for kind, level, payload in blocks:
            if kind == "heading":
                doc.add_heading(payload, level=min(level, 3))
            elif kind == "table":
                write_table(doc, payload)
            elif kind == "title":
                para = doc.add_paragraph()
                para.paragraph_format.line_spacing = 1.5
                para.paragraph_format.space_after = Pt(18)
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = para.add_run(payload)
                run.bold = True
                run.font.size = Pt(BODY_PT + 4)
            elif kind == "caption":
                add_caption(doc, payload)
            elif kind == "figure":
                write_figure(doc, payload)
            elif kind == "csv":
                write_csv_table(doc, payload)
            else:
                if payload.strip().startswith("The principal finding is that"):
                    payload = HEADLINE_NEW
                para = doc.add_paragraph()
                if payload.startswith("**Table") or payload.startswith("Table "):
                    para.paragraph_format.line_spacing = 1.0
                    para.paragraph_format.space_after = Pt(6)
                    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                add_runs(para, payload)

    emit(abstract)
    emit(intro_blocks)
    emit(methods)
    emit(results)
    emit(discussion)

    doc.add_heading("References", level=2)
    for n in sorted(refs):
        para = doc.add_paragraph()
        para.paragraph_format.line_spacing = 1.5
        para.paragraph_format.space_after = Pt(6)
        para.paragraph_format.left_indent = Inches(0.5)
        para.paragraph_format.first_line_indent = Inches(-0.5)
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        para.add_run(f"[{n}] {refs[n]}")

    doc.save(out)

    def citations(text):
        """Numbers cited in a span, expanding ranges such as [4-10,17-25]."""
        found = set()
        for group in re.findall(r"\[([0-9,\s\u2013\u2014-]+)\]", text):
            for item in group.replace(" ", "").split(","):
                span = re.match(r"^(\d+)[\u2013\u2014-](\d+)$", item)
                if span:
                    found.update(range(int(span.group(1)), int(span.group(2)) + 1))
                elif item.isdigit():
                    found.add(int(item))
        return found

    cited = set()
    for blocks in (abstract, intro_blocks, methods, results, discussion):
        for kind, _, payload in blocks:
            if kind == "para":
                cited |= citations(payload)
            elif kind == "table":
                for row in payload:
                    for cell in row:
                        cited |= citations(cell)
    missing = sorted(cited - set(refs))
    unused = sorted(set(refs) - cited)

    print(f"  saved {out.name}")
    print(f"  paragraphs {len(doc.paragraphs)}, tables {len(doc.tables)}, "
          f"references {len(refs)}")
    print(f"  distinct citations in text: {len(cited)}")
    if missing:
        print(f"  CITED BUT NOT LISTED: {missing}")
    if unused:
        print(f"  listed but never cited: {unused}")


if __name__ == "__main__":
    main()
