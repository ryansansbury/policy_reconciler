"""Keep a review in SQLite, so every finding can be traced to its clauses and every clause to its file.

One database per library. The tables are the documents, their sections and clauses, the atoms read from them, the
findings and variations, and the queue of clauses code couldn't read. Lists and values are stored as JSON text.
"""
import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE documents (key TEXT PRIMARY KEY, id TEXT, version INTEGER, title TEXT, type TEXT, format TEXT,
                        file TEXT, effective TEXT, owner TEXT, applies_to TEXT, states TEXT, lines TEXT);
CREATE TABLE sections (doc TEXT, idx INTEGER, heading TEXT, PRIMARY KEY (doc, idx));
CREATE TABLE clauses (id TEXT PRIMARY KEY, doc TEXT, section INTEGER, kind TEXT, text TEXT, fingerprint TEXT);
CREATE TABLE atoms (clause TEXT, attribute TEXT, value TEXT, value_text TEXT, states TEXT, lines TEXT,
                    explicit INTEGER, scope_text TEXT, decided_by TEXT);
CREATE TABLE findings (n INTEGER PRIMARY KEY, type TEXT, attribute TEXT, clauses TEXT, detail TEXT, decided_by TEXT);
CREATE TABLE variations (attribute TEXT, clauses TEXT, reason TEXT);
CREATE TABLE queue (clause TEXT, reasons TEXT);
"""


def fingerprint(text):
    import hashlib
    return hashlib.sha256(" ".join(text.lower().split()).encode()).hexdigest()[:16]


def save(result, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    db = sqlite3.connect(str(path))
    try:
        db.executescript(SCHEMA)
        for d in result["documents"]:
            db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                       (d["key"], d["id"], d["version"], d["title"], d.get("type"), d["format"], d["file"],
                        d["effective"], d["owner"], d["applies_to"], json.dumps(d.get("states")), json.dumps(d.get("lines"))))
            for s in d["sections"]:
                db.execute("INSERT INTO sections VALUES (?,?,?)", (d["key"], s["index"], s["heading"]))
                for c in s["clauses"]:
                    db.execute("INSERT INTO clauses VALUES (?,?,?,?,?,?)",
                               (c["id"], d["key"], s["index"], c["kind"], c["text"], fingerprint(c["text"])))
        for a in result["atoms"]:
            db.execute("INSERT INTO atoms VALUES (?,?,?,?,?,?,?,?,?)",
                       (a["clause"], a["attribute"], json.dumps(a["value"], sort_keys=True), a["value_text"],
                        json.dumps(a["states"]), json.dumps(a["lines"]), int(a["explicit"]), a["scope_text"],
                        a["decided_by"]))
        for n, f in enumerate(result["findings"], 1):
            detail = {k: v for k, v in f.items() if k not in ("type", "attribute", "clauses", "decided_by")}
            db.execute("INSERT INTO findings VALUES (?,?,?,?,?,?)",
                       (n, f["type"], f.get("attribute"), json.dumps(f["clauses"]), json.dumps(detail, sort_keys=True),
                        f["decided_by"]))
        for v in result["variations"]:
            db.execute("INSERT INTO variations VALUES (?,?,?)", (v["attribute"], json.dumps(v["clauses"]), v["reason"]))
        for q in result["queue"]:
            db.execute("INSERT INTO queue VALUES (?,?)", (q["clause"], json.dumps(q["reasons"])))
        db.commit()
    finally:
        db.close()
    return path


def counts(path):
    db = sqlite3.connect(str(path))
    try:
        return {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("documents", "sections", "clauses", "atoms", "findings", "variations", "queue")}
    finally:
        db.close()
