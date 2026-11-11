"""Write each document the way a bank's intranet actually holds it: Word files, intranet pages and Markdown notes.

DOCX is written with the standard library, since a .docx file is a zip of XML parts. Every archive entry carries a
fixed timestamp, so the same seed always produces the same bytes.
"""
import html
import zipfile
from datetime import date
from xml.sax.saxutils import escape

from generate import bank, taxonomy

LIST_HEADINGS = {"Steps", "Checklist", "Steps to follow"}
FIXED_TIME = (2026, 10, 1, 0, 0, 0)


def long_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def applies_to(doc):
    if set(doc["states"]) == set(bank.STATES):
        where = "All branches"
    else:
        where = " and ".join(bank.STATE_NAMES[s] for s in doc["states"]) + " branches"
    if set(doc["lines"]) == set(taxonomy.ALL_LINES):
        lines = "All business lines"
    else:
        phrase = taxonomy.line_phrase(doc["lines"])
        lines = phrase[0].upper() + phrase[1:] + " accounts"
    return f"{where}. {lines}."


def meta(doc, iso_dates=False):
    return [("Document ID", doc["id"]), ("Version", str(doc["version"])),
            ("Effective date", doc["effective"] if iso_dates else long_date(doc["effective"])),
            ("Owner", f"{doc['dept']}, {doc['owner']}"), ("Applies to", applies_to(doc))]


def file_name(doc):
    return f"{doc['id']}_v{doc['version']}.{doc['format']}"


# DOCX ------------------------------------------------------------------------------------------------------------

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def w_para(text, style=None):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{ppr}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def w_table(rows, header=None):
    out = ['<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/></w:tblPr>']
    for i, row in enumerate(([header] if header else []) + rows):
        cells = "".join(f'<w:tc>{w_para(c, "TableHeader" if header and i == 0 else None)}</w:tc>' for c in row)
        out.append(f"<w:tr>{cells}</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


STYLES_XML = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              f'<w:styles xmlns:w="{W}">'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
              '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="ListNumber"><w:name w:val="List Number"/></w:style>'
              '<w:style w:type="paragraph" w:styleId="TableHeader"><w:name w:val="Table Header"/><w:rPr><w:b/></w:rPr></w:style>'
              '<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/></w:style>'
              '</w:styles>')
CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                 '<Default Extension="xml" ContentType="application/xml"/>'
                 '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                 '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                 '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                 '</Types>')
ROOT_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
             '</Relationships>')
DOC_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>')


def core_xml(doc):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(doc["title"])}</dc:title><dc:creator>{escape(doc["owner"])}</dc:creator>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{doc["effective"]}T00:00:00Z</dcterms:created>'
            '</cp:coreProperties>')


def docx_bytes(doc):
    body = [w_para(doc["title"], "Title"), w_table([list(r) for r in meta(doc)])]
    for sec in doc["sections"]:
        body.append(w_para(sec["heading"], "Heading1"))
        if sec["table"]:
            body.append(w_table([c["cells"] for c in sec["clauses"]], header=["Item", "Requirement"]))
            continue
        style = "ListNumber" if sec["heading"] in LIST_HEADINGS else None
        body += [w_para(c["text"], style) for c in sec["clauses"]]
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>'
                + "".join(body) + "<w:sectPr/></w:body></w:document>")
    parts = [("[Content_Types].xml", CONTENT_TYPES), ("_rels/.rels", ROOT_RELS), ("docProps/core.xml", core_xml(doc)),
             ("word/_rels/document.xml.rels", DOC_RELS), ("word/document.xml", document), ("word/styles.xml", STYLES_XML)]
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in parts:
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, text.encode("utf-8"))
    return buf.getvalue()


# HTML ------------------------------------------------------------------------------------------------------------

def html_text(doc):
    e = html.escape
    out = ["<!DOCTYPE html>", '<html lang="en"><head><meta charset="utf-8">', f"<title>{e(doc['title'])}</title>",
           "</head><body>", '<header class="doc-meta">', f"<h1>{e(doc['title'])}</h1>", "<dl>"]
    out += [f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in meta(doc)]
    out += ["</dl>", "</header>"]
    for sec in doc["sections"]:
        out += ["<section>", f"<h2>{e(sec['heading'])}</h2>"]
        if sec["table"]:
            out.append("<table><thead><tr><th>Item</th><th>Requirement</th></tr></thead><tbody>")
            out += [f"<tr><td>{e(c['cells'][0])}</td><td>{e(c['cells'][1])}</td></tr>" for c in sec["clauses"]]
            out.append("</tbody></table>")
        elif sec["heading"] in LIST_HEADINGS:
            out.append("<ol>" + "".join(f"<li>{e(c['text'])}</li>" for c in sec["clauses"]) + "</ol>")
        else:
            out += [f"<p>{e(c['text'])}</p>" for c in sec["clauses"]]
        out.append("</section>")
    out.append("</body></html>")
    return "\n".join(out) + "\n"


# Markdown --------------------------------------------------------------------------------------------------------

def md_text(doc):
    out = [f"# {doc['title']}", ""]
    out += [f"**{k}:** {v}  " for k, v in meta(doc, iso_dates=True)]
    out.append("")
    for sec in doc["sections"]:
        out += [f"## {sec['heading']}", ""]
        if sec["table"]:
            out += ["| Item | Requirement |", "|---|---|"]
            out += [f"| {c['cells'][0]} | {c['cells'][1]} |" for c in sec["clauses"]]
            out.append("")
        elif sec["heading"] in LIST_HEADINGS:
            out += [f"{i}. {c['text']}" for i, c in enumerate(sec["clauses"], 1)]
            out.append("")
        else:
            for c in sec["clauses"]:
                out += [c["text"], ""]
    return "\n".join(out).rstrip() + "\n"


def write(doc, folder):
    """Write one document into folder and return its file name."""
    name = file_name(doc)
    path = folder.joinpath(name)
    if doc["format"] == "docx":
        path.write_bytes(docx_bytes(doc))
    elif doc["format"] == "html":
        path.write_text(html_text(doc), encoding="utf-8")
    else:
        path.write_text(md_text(doc), encoding="utf-8")
    return name
