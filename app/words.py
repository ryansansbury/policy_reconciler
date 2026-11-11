"""Every visible word lives in WORDS.md, so the wording changes in one place.

Each `## key` heading starts an entry, and the text under it, up to the next heading, is its value. Lines inside a
paragraph join with spaces and paragraphs stay apart. A profile (profiles/<name>/words.md) can override any key or
add its own, which is how one codebase builds both a client's version and the public one. A key the page asks for
that neither file has fails the build, so nothing ships blank. Curly-brace names are filled by fill().
"""
import re
import string
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
BASE = HERE.joinpath("WORDS.md")
PROFILES = HERE.joinpath("profiles")
KEY = re.compile(r"^##\s+([A-Za-z0-9_.]+)\s*$")


class MissingWord(KeyError):
    pass


def parse(text, source="WORDS.md"):
    """({key: value}, {key: raw lines}) from one words file. A key used twice in one file is an error."""
    out, raw, key, buf = {}, {}, None, []

    def flush():
        if key is None:
            return
        if key in out:
            raise ValueError(f"{source} uses the key {key} twice")
        paras = [" ".join(p.split()) for p in "\n".join(buf).strip().split("\n\n") if p.strip()]
        out[key] = "\n\n".join(paras)
        raw[key] = "\n".join(buf)

    for line in text.splitlines():
        m = KEY.match(line)
        if m:
            flush()
            key, buf = m.group(1), []
        elif key is not None:
            buf.append(line)
    flush()
    return out, raw


class Words:
    def __init__(self, entries, raw, profile):
        self.entries, self.raw, self.profile = dict(entries), dict(raw), profile
        self.used = set()

    def __getitem__(self, key):
        if key not in self.entries:
            raise MissingWord(f"no words entry for {key} in WORDS.md or the {self.profile} profile")
        self.used.add(key)
        return self.entries[key]

    def __contains__(self, key):
        return key in self.entries

    def get(self, key, default=None):
        return self[key] if key in self.entries else default

    def fill(self, key, **values):
        """The entry with its {names} filled. A name the entry uses that isn't passed is an error."""
        text = self[key]
        names = {f for _, f, _, _ in string.Formatter().parse(text) if f}
        missing = names - set(values)
        if missing:
            raise MissingWord(f"{key} needs {', '.join(sorted(missing))}")
        return text.format(**values)

    def paragraphs(self, key):
        return self[key].split("\n\n")

    def table(self, key):
        """{name: label} from an entry written as lines of '- name = label'."""
        self[key]
        out = {}
        for line in self.raw.get(key, "").splitlines():
            line = line.strip()
            if line.startswith("- ") and " = " in line:
                name, _, label = line[2:].partition(" = ")
                out[name.strip()] = label.strip()
        return out


def profiles():
    """The profile names that exist, from the folders under profiles/."""
    return sorted(p.name for p in PROFILES.iterdir() if p.joinpath("words.md").exists())


def default_profile():
    """A client's profile when one is present, and the public one otherwise, so the public copy builds itself."""
    return next((p for p in profiles() if p != "general"), "general")


def load(profile=None, base=None, profile_root=None):
    """The base words with the profile's overrides on top."""
    profile = profile or default_profile()
    entries, raw = parse(Path(base or BASE).read_text(encoding="utf-8"))
    over = Path(profile_root or PROFILES).joinpath(profile, "words.md")
    if not over.exists():
        raise FileNotFoundError(f"no profile named {profile}")
    o_entries, o_raw = parse(over.read_text(encoding="utf-8"), source=f"profiles/{profile}/words.md")
    entries.update(o_entries)
    raw.update(o_raw)
    return Words(entries, raw, profile)
