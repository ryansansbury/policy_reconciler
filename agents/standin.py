"""A stand-in model for tests and dry runs. It answers model(system, user) like any backend, with no network.

By default it reads no rules and labels every pair consistent, which is enough to drive the recorder, the
validation and the replay end to end. Tests hand in their own answer for each item, as a function of the item and
whether the call is a repair request. An answer of None leaves the item out of the reply.
"""
import json

from agents.steps import REPAIR_NOTE, STEPS


def first_words(text, n=4):
    return " ".join(text.split()[:n])


def no_rules(item, repair=False):
    return []


def consistent(item, repair=False):
    return {"label": "consistent", "quote_a": first_words(item["a"]["text"]), "quote_b": first_words(item["b"]["text"]),
            "rationale": "The stand-in labels every pair consistent."}


class StandIn:
    def __init__(self, extract=None, classify=None, name="stand-in", **more):
        self.answers = dict({"extract": extract or no_rules, "classify": classify or consistent}, **more)
        self.name = name
        self.calls = []

    def __call__(self, system, user):
        data, _ = json.JSONDecoder().raw_decode(user)
        step = next(s for s, v in STEPS.items() if v["many"] in data)
        key, many = STEPS[step]["key"], STEPS[step]["many"]
        repair = REPAIR_NOTE in user
        results = []
        for item in data[many]:
            got = self.answers[step](item, repair)
            if got is None:
                continue
            results.append({"clause": item["clause"], "atoms": got} if step == "extract" else dict(got, **{key: item[key]}))
        text = json.dumps({"results": results})
        self.calls.append({"step": step, "items": [i[key] for i in data[many]], "repair": repair})
        return text, {"ms": 0, "input_tokens": len(system + user) // 4, "output_tokens": len(text) // 4,
                      "cost_usd": 0.0, "models": [self.name]}

    def described(self):
        return {"backend": "stand-in", "model": self.name}
