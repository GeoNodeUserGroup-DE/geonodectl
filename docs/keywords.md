# Keywords

Manage free-text keywords and thesaurus keywords in GeoNode.

---

## Free-text keywords (`keywords`)

```bash
geonodectl keywords list
geonodectl keywords describe 5
```

---

## Thesaurus keywords (`tkeywords` / `thesaurikeywords`)

Structured keywords drawn from a registered thesaurus (e.g. INSPIRE, GEMET).

```bash
geonodectl tkeywords list
geonodectl tkeywords describe 3
```

With the `geonodectl-zalf` extension installed, `tkeywords list` also shows the `keyword`
identifier the ZALF GeoNode backend returns.

---

## Thesaurus keyword labels (`tkeywordlabels`)

Language-specific labels for thesaurus keywords. Vanilla GeoNode does not offer this endpoint,
so the command comes from the `geonodectl-zalf` extension, see [extensions.md](extensions.md).

```bash
pip install geonodectl-zalf
geonodectl tkeywordlabels list
geonodectl tkeywordlabels describe soil
```
