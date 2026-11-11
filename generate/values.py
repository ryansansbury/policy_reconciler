"""How the generator writes values into policy text, in the several ways real documents write them.

A value is a small dict: {"type": ..., plus its fields}. The generator renders it as text here. The engine never
imports this module. It parses text back into values with its own code, which is the point of the test.
"""

ONES = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen")
TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")


def words(n):
    """A whole number from 0 to 999,999 in words, the way a policy writes it ("twenty-five")."""
    if n < 20:
        return ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        return TENS[t] + ("-" + ONES[o] if o else "")
    if n < 1000:
        h, rest = divmod(n, 100)
        return ONES[h] + " hundred" + (" " + words(rest) if rest else "")
    th, rest = divmod(n, 1000)
    return words(th) + " thousand" + (" " + words(rest) if rest else "")


def money(dollars, style="digits"):
    if style == "words":
        return words(dollars) + (" dollar" if dollars == 1 else " dollars")
    return "${:,}".format(dollars)


def clock(minutes, style="colon_pm"):
    h, m = divmod(minutes, 60)
    h12 = h - 12 if h > 12 else h
    suffix_upper = "PM" if h >= 12 else "AM"
    suffix_lower = "p.m." if h >= 12 else "a.m."
    if style == "colon_lower":
        return f"{h12}:{m:02d} {suffix_lower}"
    if style == "short":
        return f"{h12} {suffix_upper}" if m == 0 else f"{h12}:{m:02d} {suffix_upper}"
    return f"{h12}:{m:02d} {suffix_upper}"


UNIT_WORD = {"days": "day", "business_days": "business day", "calendar_days": "calendar day",
             "months": "month", "years": "year"}


def duration(n, unit, style="digits"):
    word = UNIT_WORD[unit]
    noun = word if n == 1 else word + "s"
    num = words(n) if style == "words" else str(n)
    return f"{num} {noun}"


def count(n, style="words"):
    return words(n) if style == "words" else str(n)


def percent(bp, style="percent"):
    """Basis points as a policy writes them: 25 is "0.25%" or "25 basis points"."""
    if style == "bp":
        return f"{bp} basis points"
    whole, frac = divmod(bp, 100)
    return f"{whole}.{frac:02d}%"


def render(value, style=None):
    """The value as text in the given style, or its default style."""
    t = value["type"]
    if t == "money":
        return money(value["dollars"], style or "digits")
    if t == "time":
        return clock(value["minutes"], style or "colon_pm")
    if t == "duration":
        return duration(value["n"], value["unit"], style or "digits")
    if t == "count":
        return count(value["n"], style or "words")
    if t == "percent":
        return percent(value["bp"], style or "percent")
    if t == "role":
        from generate.bank import ROLES
        return ROLES[value["role"]]
    raise ValueError(f"no text form for value type {t}")


STYLES = {
    "money": ("digits", "digits", "digits", "words"),
    "time": ("colon_pm", "colon_lower", "short"),
    "duration": ("digits", "digits", "words"),
    "count": ("words", "words", "digits"),
    "percent": ("percent", "percent", "bp"),
    "role": (None,),
}


def key(value):
    """A comparable, hashable form of a value, used in the answer key."""
    t = value["type"]
    if t == "money":
        return ("money", value["dollars"])
    if t == "time":
        return ("time", value["minutes"])
    if t == "duration":
        return ("duration", value["n"], value["unit"])
    if t in ("count",):
        return ("count", value["n"])
    if t == "percent":
        return ("percent", value["bp"])
    if t == "role":
        return ("role", value["role"])
    if t == "modal":
        return ("modal", value["modal"])
    raise ValueError(t)


def make(t, *args):
    """Shorthand constructor: make("money", 50), make("duration", 2, "business_days"), make("role", "teller")."""
    if t == "money":
        return {"type": "money", "dollars": args[0]}
    if t == "time":
        return {"type": "time", "minutes": args[0]}
    if t == "duration":
        return {"type": "duration", "n": args[0], "unit": args[1]}
    if t == "count":
        return {"type": "count", "n": args[0]}
    if t == "percent":
        return {"type": "percent", "bp": args[0]}
    if t == "role":
        return {"type": "role", "role": args[0]}
    if t == "modal":
        return {"type": "modal", "modal": args[0]}
    raise ValueError(t)
