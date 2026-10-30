# loom-view/1: the data contract between the data stage and the scene generator

One JSON file, `loom-view.json`, written by the data stage (merge) and read by the scene generator.
It is a PUBLIC-CANDIDATE view: people flagged living_possible (or presumed living: no death and born within 110 years of asof) are left out,
and so are unions that touch them. Years are integers (the best single year; precision kept beside it).

```json
{
  "version": "loom-view/1",
  "asof": 2026,
  "built": {"by": "<script name>", "inputs": {"<path>": "<sha256>"}, "gates": {"errors": 0, "warnings": 0}},
  "families": [
    {
      "key": "rothschild",                     // also "habsburg", "darwin_wedgwood"
      "name": "Rothschild",
      "dyes": {"rothschild": {"founders": ["<id>", "<id>"], "color": "#9e1b1b"}},
      "houses": [
        {"key": "frankfurt", "name": "Frankfurt", "lon": 8.68, "lat": 50.11, "opened": 1744, "closed": 1901, "note": "..."}
      ],
      "people": [
        {"id": "Q57949", "qid": "Q57949", "name": "Nathan Mayer Rothschild", "short": "Nathan",
         "sex": "M", "born": 1777, "born_precision": "year", "died": 1836, "died_precision": "day",
         "house": "london", "core": true, "family": "Rothschild",
         "father": "<id>|null", "mother": "<id>|null",
         "shares": {"rothschild": 1.0},          // exact expected fraction of descent from each dye's founders (founder = 1, unrelated in-law = 0, child = mean of parents)
         "generation": [1, 1],                   // min and max steps from the founders over all paths
         "confidence": "Confirmed|Likely|Suspected",
         "wikipedia": "https://en.wikipedia.org/wiki/...", "note": "<= 240 chars", "sources": ["..."]}
      ],
      "unions": [
        {"id": "U-<a>-<b>", "a": "<id>", "b": "<id>", "year": 1824, "year_precision": "year|circa|unknown",
         "close": true, "relationship": "uncle-niece", "phi": 0.125, "confidence": "Likely"}
      ],
      "events": [
        {"year": 1822, "label": "The five brothers are made barons", "grade": "C", "source": "<url>"}
      ]
    }
  ]
}
```

Rules:
- `house` is where the person's thread runs: for a core member, the bank house / line / household they belonged to as an adult;
  for an in-law, the house of their spouse at marriage. The data stage records the rule it used in `built`.
- Habsburg houses are lines mapped to a seat (e.g. Vienna, Madrid, Innsbruck, Graz, Prague, Brussels); Darwin-Wedgwood houses are
  households (e.g. Etruria/Maer, Shrewsbury, Down, Cambridge). Coordinates are the seat's.
- `close` is true when the two spouses share a known common ancestor in the data (phi > 0); phi is their kinship coefficient (exact, lower bound).
- `events` are optional and only graded C (checked) or L (one secondary source) ones are allowed.
- A missing parent is null, never a guess. A person who is in unions but has no house gets the spouse's house.
