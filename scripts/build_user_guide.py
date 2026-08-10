from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "WURKIO_Stock_Scanner_Getting_Started.docx"
NAVY = "17365D"
BLUE = "2E74B5"
LIGHT_BLUE = "E8EEF5"
PALE = "F4F6F9"
GRAY = "5B6573"
WHITE = "FFFFFF"
WIDTH_DXA = 9360


def shade(cell, color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), color)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths):
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    tbl_w.set(qn("w:w"), str(sum(widths)))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), "120")
    tbl_ind.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = Inches(width / 1440)
            tc_w = cell._tc.get_or_add_tcPr().find(qn("w:tcW"))
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)


def style_run(run, size=11, bold=False, color="000000", italic=False, font="Calibri"):
    run.font.name = font
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), font)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), font)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def add_body(doc, text, bold_lead=None):
    p = doc.add_paragraph()
    if bold_lead and text.startswith(bold_lead):
        style_run(p.add_run(bold_lead), bold=True)
        style_run(p.add_run(text[len(bold_lead):]))
    else:
        style_run(p.add_run(text))
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    style_run(p.add_run(text))
    return p


def add_number(doc, text):
    p = doc.add_paragraph(style="List Number")
    style_run(p.add_run(text))
    return p


def add_code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.right_indent = Inches(0.15)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(8)
    shade_paragraph(p, "EEF2F6")
    style_run(p.add_run(text), size=9.5, color=NAVY, font="Consolas")
    return p


def shade_paragraph(paragraph, color):
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    p_pr.append(shd)


def add_callout(doc, label, text, color=LIGHT_BLUE):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.12)
    p.paragraph_format.right_indent = Inches(0.12)
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(9)
    shade_paragraph(p, color)
    style_run(p.add_run(label + "  "), bold=True, color=NAVY)
    style_run(p.add_run(text), color=NAVY)


def add_table(doc, headers, rows, widths):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    set_table_geometry(table, widths)
    for i, header in enumerate(headers):
        shade(table.rows[0].cells[i], LIGHT_BLUE)
        p = table.rows[0].cells[i].paragraphs[0]
        style_run(p.add_run(header), size=9.5, bold=True, color=NAVY)
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            p = cells[i].paragraphs[0]
            style_run(p.add_run(str(value)), size=9.25)
    set_table_geometry(table, widths)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def heading(doc, text, level=1):
    p = doc.add_paragraph(text, style=f"Heading {level}")
    return p


def configure_styles(doc):
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25
    for name, size, color, before, after in (
        ("Heading 1", 16, BLUE, 18, 10),
        ("Heading 2", 13, BLUE, 14, 7),
        ("Heading 3", 12, NAVY, 10, 5),
    ):
        style = styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
    for name in ("List Bullet", "List Bullet 2", "List Number"):
        style = styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.25
    styles["List Bullet"].paragraph_format.left_indent = Inches(0.375)
    styles["List Bullet"].paragraph_format.first_line_indent = Inches(-0.188)
    styles["List Number"].paragraph_format.left_indent = Inches(0.375)
    styles["List Number"].paragraph_format.first_line_indent = Inches(-0.188)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    style_run(paragraph.add_run("WURKIO Stock Scanner  |  "), size=9, color=GRAY)
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.extend((fld_begin, instr, fld_end))


def build():
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    configure_styles(doc)
    add_page_number(section.footer.paragraphs[0])

    # Cover: editorial_cover pattern, compact_reference_guide preset.
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(105)
    p.paragraph_format.space_after = Pt(14)
    style_run(p.add_run("WURKIO TRADING LAB"), size=11, bold=True, color=BLUE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(9)
    style_run(p.add_run("WURKIO Stock Scanner"), size=30, bold=True, color=NAVY)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(36)
    style_run(p.add_run("Getting Started, Controls & Functions"), size=15, color=GRAY)
    add_callout(doc, "CURRENT VERSION", "CSV-based Python scanner engine with configurable JSON presets, ranked scoring, table output, and JSON output.")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(75)
    style_run(p.add_run("Version 0.2  |  August 2026"), size=10.5, color=GRAY)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(p.add_run("For educational and research use; not financial advice."), size=9.5, italic=True, color=GRAY)
    doc.add_page_break()

    heading(doc, "1. What the scanner does")
    add_body(doc, "WURKIO reads a snapshot of stock data from a CSV file, calculates derived metrics, applies every enabled filter, assigns each passing stock a score from 0 to 100, and ranks the results.")
    add_callout(doc, "WORKFLOW", "Market snapshot CSV  >  calculated metrics  >  enabled filters  >  WURKIO score  >  ranked results")
    heading(doc, "What is included now", 2)
    for item in (
        "Configurable filters for price, volume, average volume, RVOL, ATR%, percent change, volume change, and float.",
        "Seven presets copied from the supplied BigFish and Early Swings screenshots.",
        "Readable terminal table output and machine-readable JSON output.",
        "Input validation and an automated test suite.",
    ):
        add_bullet(doc, item)
    heading(doc, "What is not included yet", 2)
    add_body(doc, "This release does not yet download live market data and does not yet include a Windows graphical interface. The current controls are command-line options and editable JSON files. The included CSV is synthetic demonstration data.")
    heading(doc, "Project layout", 2)
    add_table(doc, ["Location", "Purpose"], [
        ("wurkio_scanner/", "Scanner models, calculations, filtering, scoring, CSV loading, and CLI."),
        ("scanner_config.json", "Default editable filter configuration."),
        ("presets/", "Seven ready-to-run screenshot configurations."),
        ("data/sample_stocks.csv", "Synthetic data for learning and testing."),
        ("tests/", "Automated checks for calculations, filters, presets, and validation."),
    ], [2700, 6660])
    doc.add_page_break()

    heading(doc, "2. First-time setup")
    heading(doc, "Install Python", 2)
    add_body(doc, "Install Python 3.10 or newer from python.org. During Windows installation, enable Add Python to PATH. Then open PowerShell and check:")
    add_code(doc, "python --version")
    add_body(doc, "If Windows uses the Python Launcher, replace python with py in every command in this guide.")
    heading(doc, "Open the project folder", 2)
    add_code(doc, 'cd "C:\\Users\\Administrator\\Documents\\WURKIO_Stock Scanner"')
    heading(doc, "Run your first scan", 2)
    add_code(doc, "python -m wurkio_scanner --input data/sample_stocks.csv --config scanner_config.json")
    add_body(doc, "A successful run prints a ranked table. If no symbols satisfy every enabled rule, the scanner prints: No stocks matched the configured filters.")
    heading(doc, "Run a saved preset", 2)
    add_code(doc, "python -m wurkio_scanner --input data/sample_stocks.csv --config presets/bigfish_scalper_v01.json")
    heading(doc, "Verify the installation", 2)
    add_code(doc, "python -m unittest discover -s tests -v")
    add_body(doc, "The final line should say OK. Test failures mean the installation or source files need attention before live data is connected.")
    doc.add_page_break()

    heading(doc, "3. Controls and filter reference")
    add_body(doc, "Edit a configuration file in any text editor. JSON keys are the controls; their values are the thresholds. Use null to disable a filter. All enabled filters are combined with AND logic, meaning a stock must pass every enabled rule.")
    add_table(doc, ["Control", "Function", "Example"], [
        ("price_min / price_max", "Inclusive last-price range.", "2 and 20"),
        ("rvol_min", "Minimum 5-day relative volume.", "1.5"),
        ("current_volume_min", "Minimum current session volume.", "300000"),
        ("avg_volume_5d_min", "Minimum five-day average volume.", "1000000"),
        ("avg_volume_20d_min", "Minimum 20-day average volume.", "1000000"),
        ("atr_percent_min / max", "Inclusive ATR% range; either boundary may be disabled.", "3 and 5"),
        ("latest_percent_change_min", "Minimum latest daily percentage change.", "3"),
        ("volume_percent_change_min", "Minimum volume increase versus 20-day average.", "30"),
        ("float_min / float_max", "Inclusive tradable-share float range.", "10M to 100M"),
    ], [2500, 4760, 2100])
    heading(doc, "Calculated functions", 2)
    add_code(doc, "RVOL = current_volume / avg_volume_5d")
    add_code(doc, "ATR% = atr_14d / price * 100")
    add_code(doc, "Volume change % = (current_volume - avg_volume_20d) / avg_volume_20d * 100")
    add_callout(doc, "IMPORTANT", "JSON uses raw numbers. Enter ten million shares as 10000000, not 10M. Percent thresholds are entered as 5 for 5%, not 0.05.", "FFF4CC")
    doc.add_page_break()

    heading(doc, "4. Configuration and presets")
    heading(doc, "Example configuration", 2)
    add_code(doc, '{\n  "price_min": 2,\n  "price_max": 20,\n  "rvol_min": 1.5,\n  "current_volume_min": 300000,\n  "avg_volume_5d_min": null,\n  "avg_volume_20d_min": 1000000,\n  "atr_percent_min": 3,\n  "atr_percent_max": null,\n  "latest_percent_change_min": 3,\n  "volume_percent_change_min": 30,\n  "float_min": 10000000,\n  "float_max": 100000000\n}')
    heading(doc, "Available presets", 2)
    add_table(doc, ["Preset file", "Main character"], [
        ("bigfish_scalper_v01.json", "RVOL 2+, ATR% 5+, price $2-$20, float 10M-100M."),
        ("early_swings_v0.1.json", "High volume and 200% volume-change threshold."),
        ("early_swings_v0.2.json", "Latest change 12%+, RVOL 1.5+, ATR% 5+."),
        ("early_swings_v0.3.json", "RVOL 2+, volume 500K+, volume change 50%+."),
        ("early_swings_v0.4.json", "ATR% constrained to 3%-5%; float 10M-100M."),
        ("early_swings_v0.5.json", "Volume 400K+, ATR% 3+, float 10M-100M."),
        ("early_swings_v0.6.json", "Volume 300K+; otherwise close to v0.5."),
    ], [3600, 5760])
    add_callout(doc, "CHECK THE SOURCE VALUES", "The screenshots show 20-day average-volume values of 500 and 1000 in some presets. They are preserved literally. If the source meant 500K or 1M, change them to 500000 or 1000000.", "FFF4CC")
    doc.add_page_break()

    heading(doc, "5. Command controls and results")
    add_table(doc, ["Command control", "Required?", "Function"], [
        ("--input PATH", "Yes", "Selects the market snapshot CSV."),
        ("--config PATH", "No", "Selects filter JSON; defaults to scanner_config.json."),
        ("--format table", "No", "Prints the human-readable ranked table; this is the default."),
        ("--format json", "No", "Prints structured results for a future GUI, API, or saved pipeline."),
        ("--help", "No", "Displays the command-line help screen."),
    ], [2400, 1400, 5560])
    heading(doc, "JSON output", 2)
    add_code(doc, "python -m wurkio_scanner --input data/sample_stocks.csv --config scanner_config.json --format json")
    heading(doc, "How ranking works", 2)
    add_body(doc, "Only passing stocks receive a result. The score averages the strength of all enabled filters and normalizes it to 100. A minimum threshold earns roughly half credit at the threshold and more credit as the metric rises, capped at 100 for that component. Range filters favor values near the center while still accepting either boundary.")
    add_body(doc, "The score is a ranking aid, not a prediction of price movement, trade quality, or profitability. When two stocks have the same score, higher RVOL ranks first, followed by symbol alphabetically.")
    heading(doc, "Worked example", 2)
    add_table(doc, ["Metric", "ABCD", "BigFish rule", "Result"], [
        ("Price", "$4.25", "$2-$20", "Pass"),
        ("5-day RVOL", "2.21", "2.0+", "Pass"),
        ("Current volume", "6.2M", "250K+", "Pass"),
        ("ATR%", "9.65%", "5%+", "Pass"),
        ("Latest change", "12.80%", "5%+", "Pass"),
        ("Float", "13.4M", "10M-100M", "Pass"),
    ], [2200, 1800, 2700, 2660])
    doc.add_page_break()

    heading(doc, "6. Preparing market data")
    add_body(doc, "The CSV must use this exact header row:")
    add_code(doc, "symbol,price,current_volume,avg_volume_5d,avg_volume_20d,atr_14d,latest_percent_change,float_shares")
    add_table(doc, ["CSV field", "Expected value"], [
        ("symbol", "Ticker symbol, such as ABCD."),
        ("price", "Latest price in dollars."),
        ("current_volume", "Current session share volume."),
        ("avg_volume_5d", "Five-day average volume used for RVOL."),
        ("avg_volume_20d", "20-day average used by the volume-change calculation."),
        ("atr_14d", "Raw 14-day average true range in dollars, not ATR%."),
        ("latest_percent_change", "Latest percentage change, such as 8.5 for 8.5%."),
        ("float_shares", "Tradable share float as a raw share count."),
    ], [2700, 6660])
    heading(doc, "Adding or replacing data", 2)
    for text in (
        "Keep the header names exactly as shown.",
        "Use one stock per row and plain numeric values without commas, dollar signs, percent signs, K, or M.",
        "Save the file as CSV UTF-8.",
        "Point --input to the new file and run the scan.",
    ):
        add_number(doc, text)
    add_callout(doc, "DATA QUALITY", "A scanner is only as current and accurate as its source data. Float can be stale, volume changes during the session, and delayed quotes can materially alter results.", "FFF4CC")
    doc.add_page_break()

    heading(doc, "7. Troubleshooting and safe use")
    add_table(doc, ["Problem", "Likely cause and fix"], [
        ("python is not recognized", "Install Python and enable Add Python to PATH, or try py instead of python."),
        ("No stocks matched", "The rules may be too strict. Disable one threshold at a time with null and rerun."),
        ("CSV is missing columns", "Restore the exact required header fields listed in Section 6."),
        ("Invalid market data on CSV line...", "Remove symbols or punctuation from numeric cells and check for blanks or negative raw values."),
        ("Invalid JSON", "Check commas, quotes, braces, and use lowercase null rather than None."),
        ("Unexpected RVOL", "Confirm avg_volume_5d contains the intended five-day average."),
        ("Unexpected volume change", "Confirm avg_volume_20d is the intended 20-day average and is not zero."),
    ], [3000, 6360])
    heading(doc, "Recommended operating routine", 2)
    for text in (
        "Refresh the source data and note its timestamp.",
        "Select or copy a preset; edit the copy when experimenting.",
        "Run the scanner and sanity-check the top candidates against a broker or trusted quote source.",
        "Review liquidity, spreads, news, halts, filings, and risk before considering any trade.",
        "Record which preset and data timestamp produced the result.",
    ):
        add_number(doc, text)
    add_callout(doc, "RISK NOTICE", "Scanner results are screening signals, not recommendations. They do not account for execution risk, slippage, halts, dilution, news quality, or your personal risk limits.", "FCE8E6")
    heading(doc, "Next development step", 2)
    add_body(doc, "Connect a licensed market-data provider through a provider interface, then add timestamping and freshness checks. After the data pipeline is dependable, the same configuration and result objects can power a Windows GUI with editable fields and a SCAN button.")

    doc.core_properties.title = "WURKIO Stock Scanner - Getting Started, Controls & Functions"
    doc.core_properties.subject = "User guide for the WURKIO Stock Scanner Python engine"
    doc.core_properties.author = "WURKIO Trading Lab"
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
