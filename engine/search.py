"""Keyword search over the published clauses by BM25, the ranking most search engines start from.

A clause scores higher the more of a question's words it holds, rarer words count for more, a word repeated in one
clause adds less each time, and long clauses are discounted so they don't win by size alone. k1 sets how fast
repeats stop adding and b sets how much length matters, at the usual values.
"""
import math
import re

WORD = re.compile(r"[a-z0-9]+")
STOP = set("a an and are as at be by can do does for from has have how i if in is it its of on or the to what when "
           "where which who will with you your".split())


def tokens(text):
    return [w for w in WORD.findall(text.lower()) if w not in STOP]


class Index:
    def __init__(self, items, k1=1.2, b=0.75):
        """items are dicts with an "id" and a "text"."""
        self.items, self.k1, self.b = list(items), k1, b
        self.toks = [tokens(i["text"]) for i in self.items]
        self.avg = sum(map(len, self.toks)) / max(1, len(self.toks))
        df = {}
        for t in self.toks:
            for w in set(t):
                df[w] = df.get(w, 0) + 1
        n = len(self.items)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def score(self, query_tokens, i):
        t = self.toks[i]
        s = 0.0
        for w in set(query_tokens):
            f = t.count(w)
            if f:
                s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(t) / self.avg))
        return s

    def search(self, query, k=5):
        """The k best items for the query, best first, each with its score."""
        q = tokens(query)
        scored = [(self.score(q, i), i) for i in range(len(self.items))]
        best = sorted((x for x in scored if x[0] > 0), key=lambda x: (-x[0], self.items[x[1]]["id"]))[:k]
        return [dict(self.items[i], score=round(s, 3)) for s, i in best]
