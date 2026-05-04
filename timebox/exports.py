from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.utils.html import escape


EXPORT_TRANSLATIONS = {
    "cs": {
        "sheet_name": "Rozpis hodin",
        "header": ["Datum", "Začátek", "Konec", "Součet hodin", "Poznámka"],
        "total_label": "Součet celkem",
    },
    "en": {
        "sheet_name": "Work schedule",
        "header": ["Date", "Start", "End", "Total hours", "Note"],
        "total_label": "Total",
    },
}


def build_work_entries_xlsx(rows, language="cs"):
    output = BytesIO()
    translations = EXPORT_TRANSLATIONS.get(language, EXPORT_TRANSLATIONS["cs"])
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_relationships_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml(translations["sheet_name"]))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships_xml())
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(rows, translations))
    return output.getvalue()


def _content_types_xml():
    return """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""


def _root_relationships_xml():
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def _workbook_xml(sheet_name):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""


def _workbook_relationships_xml():
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def _styles_xml():
    return """<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>"""


def _worksheet_xml(rows, translations):
    sheet_rows = [_row_xml(1, translations["header"], style=1)]
    row_index = 2
    total_hours = None
    for row in rows:
        total_hours = row.duration_hours if total_hours is None else total_hours + row.duration_hours
        sheet_rows.append(
            _row_xml(
                row_index,
                [
                    row.date.isoformat(),
                    row.start_time.strftime("%H:%M"),
                    row.end_time.strftime("%H:%M"),
                    row.duration_hours,
                    row.note,
                ],
            )
        )
        row_index += 1
    if total_hours is not None:
        sheet_rows.append(_total_row(row_index, total_hours, translations["total_label"]))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <cols>
    <col min="1" max="1" width="12" customWidth="1"/>
    <col min="2" max="4" width="14" customWidth="1"/>
    <col min="5" max="5" width="40" customWidth="1"/>
  </cols>
  <sheetData>
    {''.join(sheet_rows)}
  </sheetData>
</worksheet>"""


def _total_row(row_index, total_hours, total_label):
    return _row_xml(row_index, ["", "", "", total_hours, total_label], style=1)


def _row_xml(row_index, values, style=None):
    cells = []
    for offset, value in enumerate(values):
        column = _column_name(offset + 1)
        style_attr = f' s="{style}"' if style else ""
        if isinstance(value, (int, float)) or value.__class__.__name__ == "Decimal":
            cells.append(f'<c r="{column}{row_index}"{style_attr}><v>{value}</v></c>')
        else:
            cells.append(f'<c r="{column}{row_index}" t="inlineStr"{style_attr}><is><t>{escape(str(value or ""))}</t></is></c>')
    return f'<row r="{row_index}">{"".join(cells)}</row>'


def _column_name(number):
    name = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        name = chr(65 + remainder) + name
    return name
