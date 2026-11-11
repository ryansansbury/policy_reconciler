"""Read a policy library the way it arrives: Word files, intranet pages and Markdown notes.

Each document becomes the same shape: its metadata (id, version, effective date, owner and what it applies to) and
its sections in order, each with its clauses. A clause is one paragraph, one list item or one table row. Clause ids
are positional (<id>@v<version>/s<section>/c<clause>), so the same file always yields the same ids.

A file the parser can't read is held with its reason, never guessed.
"""
import html.parser
import re
import zipfile
from datetime import datetime
from xml.etree import ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
META_KEYS = {"document id": "id", "version": "version", "effective date": "effective", "owner": "owner",
             "applies to": "applies_to"}


class Unreadable(ValueError):
    pass


def iso_date(text):
    text = text.strip()
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    raise Unreadable(f"unreadable effective date: {text!r}")


def finish(title, meta, sections, fmt, name):
    missing = [k for k in ("id", "version", "effective") if k not in meta]
    if missing:
        raise Unreadable(f"{name} has no {', '.join(missing)}")
    try:
        version = int(meta["version"])
    except ValueError:
        raise Unreadable(f"{name} has an unreadable version {meta['version']!r}")
    doc = {"id": meta["id"].strip(), "version": version, "title": title.strip(), "format": fmt, "file": name,
           "effective": iso_date(meta["effective"]), "owner": meta.get("owner", "").strip(),
           "applies_to": meta.get("applies_to", "").strip(), "sections": []}
    doc["key"] = f"{doc['id']}@v{doc['version']}"
    for si, (heading, clauses) in enumerate(sections, 1):
        sec = {"index": si, "heading": heading.strip(), "clauses": []}
        for ci, (kind, text, cells) in enumerate(clauses, 1):
            cl = {"id": f"{doc['key']}/s{si}/c{ci}", "kind": kind, "text": " ".join(text.split())}
            if cells:
                cl["cells"] = [" ".join(c.split()) for c in cells]
            sec["clauses"].append(cl)
        doc["sections"].append(sec)
    return doc


# Word ------------------------------------------------------------------------------------------------------------

def para_text(p):
    return "".join(t.text or "" for t in p.iter(W + "t"))


def para_style(p):
    s = p.find(f"{W}pPr/{W}pStyle")
    return s.get(W + "val") if s is not None else None


def table_rows(tbl):
    rows = []
    for tr in tbl.findall(W + "tr"):
        cells = [" ".join(para_text(p) for p in tc.findall(W + "p")) for tc in tr.findall(W + "tc")]
        header = any(para_style(p) == "TableHeader" for tc in tr.findall(W + "tc") for p in tc.findall(W + "p"))
        rows.append((cells, header))
    return rows


def parse_docx(data, name):
    try:
        with zipfile.ZipFile(data) as z:
            root = ElementTree.fromstring(z.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as e:
        raise Unreadable(f"{name} is not a readable Word file: {e}")
    body = root.find(W + "body")
    title, meta, sections, current = "", {}, [], None
    for el in body:
        if el.tag == W + "p":
            style, text = para_style(el), para_text(el)
            if not text.strip():
                continue
            if style == "Title":
                title = text
            elif style and style.startswith("Heading"):
                current = (text, [])
                sections.append(current)
            elif current is not None:
                current[1].append(("item" if style == "ListNumber" else "para", text, None))
        elif el.tag == W + "tbl":
            rows = table_rows(el)
            if current is None:
                for cells, _ in rows:
                    if len(cells) >= 2 and cells[0].strip().lower() in META_KEYS:
                        meta[META_KEYS[cells[0].strip().lower()]] = cells[1]
            else:
                for cells, header in rows:
                    if not header and any(c.strip() for c in cells):
                        current[1].append(("row", " | ".join(cells), cells))
    return finish(title, meta, sections, "docx", name)


# HTML ------------------------------------------------------------------------------------------------------------

class _Html(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.meta, self.sections = "", {}, []
        self.stack, self.buf, self.dt, self.row, self.in_head_row = [], [], None, None, False

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)
        if tag in ("h1", "h2", "h3", "p", "li", "dt", "dd", "td", "th"):
            self.buf = []
        if tag == "tr":
            self.row = []
        if tag == "thead":
            self.in_head_row = True

    def handle_endtag(self, tag):
        text = " ".join("".join(self.buf).split())
        if tag == "h1":
            self.title = text
        elif tag in ("h2", "h3"):
            self.sections.append((text, []))
        elif tag == "dt":
            self.dt = text.lower()
        elif tag == "dd" and self.dt in META_KEYS:
            self.meta[META_KEYS[self.dt]] = text
        elif tag in ("p", "li") and self.sections and "header" not in self.stack[:-1]:
            if text:
                self.sections[-1][1].append(("item" if tag == "li" else "para", text, None))
        elif tag in ("td", "th") and self.row is not None:
            self.row.append(text)
        elif tag == "tr" and self.row is not None:
            if not self.in_head_row and self.sections and any(self.row):
                self.sections[-1][1].append(("row", " | ".join(self.row), self.row))
            self.row = None
        elif tag == "thead":
            self.in_head_row = False
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_data(self, data):
        self.buf.append(data)


def parse_html(text, name):
    p = _Html()
    try:
        p.feed(text)
    except Exception as e:  # noqa: BLE001 - any parser failure holds the file
        raise Unreadable(f"{name} is not readable HTML: {e}")
    return finish(p.title, p.meta, p.sections, "html", name)


# Markdown --------------------------------------------------------------------------------------------------------

META_LINE = re.compile(r"^\*\*([^*]+):\*\*\s*(.*?)\s*$")
LIST_ITEM = re.compile(r"^\d+\.\s+(.*)$")


def parse_md(text, name):
    title, meta, sections, current, para = "", {}, [], None, []

    def flush():
        if para and current is not None:
            current[1].append(("para", " ".join(para), None))
        para.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            title = line[2:]
            continue
        if line.startswith("## ") or line.startswith("### "):
            flush()
            current = (line.split(" ", 1)[1], [])
            sections.append(current)
            continue
        m = META_LINE.match(line)
        if m and current is None:
            k = m.group(1).strip().lower()
            if k in META_KEYS:
                meta[META_KEYS[k]] = m.group(2)
            continue
        if current is None:
            continue
        if not line.strip():
            flush()
            continue
        item = LIST_ITEM.match(line)
        if item:
            flush()
            current[1].append(("item", item.group(1), None))
        elif line.startswith("|"):
            flush()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set("".join(cells)) <= set("-: ") or [c.lower() for c in cells] == ["item", "requirement"]:
                continue
            current[1].append(("row", " | ".join(cells), cells))
        else:
            para.append(line.strip())
    flush()
    return finish(title, meta, sections, "md", name)


def parse_file(path):
    name = path.name
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return parse_docx(str(path), name)
    if suffix in (".html", ".htm"):
        return parse_html(path.read_text(encoding="utf-8"), name)
    if suffix in (".md", ".markdown"):
        return parse_md(path.read_text(encoding="utf-8"), name)
    raise Unreadable(f"{name} has a format this build doesn't read yet")


def parse_folder(folder):
    """(documents, held) for every file in a folder, in name order."""
    docs, held = [], []
    for path in sorted(p for p in folder.iterdir() if p.is_file()):
        try:
            docs.append(parse_file(path))
        except Unreadable as e:
            held.append({"file": path.name, "reason": str(e)})
    return docs, held
