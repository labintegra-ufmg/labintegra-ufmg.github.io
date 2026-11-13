#!/usr/bin/env python3
"""Para cada DOI de data/publicacoes/auto.yaml consulta Crossref, OpenCitations e Semantic Scholar
e mantem o MAIOR valor de citacoes (nunca diminui). Rodar depois de orcid_sync.py."""
import os, time
from pathlib import Path
import requests, yaml

ROOT = Path(__file__).resolve().parent.parent
F = ROOT / "data" / "publicacoes" / "auto.yaml"
MAIL = os.environ.get("OPENALEX_MAILTO", "")
S = requests.Session()
S.headers["User-Agent"] = f"LabIntegra-site (mailto:{MAIL})"


def get(url, **kw):
    try:
        r = S.get(url, timeout=25, **kw)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def crossref(doi):
    j = get(f"https://api.crossref.org/works/{doi}", params={"mailto": MAIL} if MAIL else None)
    return int(j["message"].get("is-referenced-by-count", 0)) if j else None


def opencit(doi):
    j = get(f"https://api.opencitations.net/index/v2/citation-count/doi:{doi}")
    try:
        return int(j[0]["count"]) if j else None
    except Exception:
        return None


def s2(doi):
    j = get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}", params={"fields": "citationCount"})
    return int(j.get("citationCount", 0)) if j else None


def lista(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for v in x.values():
            if isinstance(v, list):
                return v
    return []


def main():
    if not F.exists():
        print("auto.yaml nao existe"); return
    data = yaml.safe_load(F.read_text(encoding="utf-8"))
    pubs = [p for p in lista(data) if isinstance(p, dict) and p.get("doi")]
    mudou = 0
    for p in pubs:
        doi = requests.utils.quote(str(p["doi"]).strip(), safe="/")
        atual = int(p.get("citacoes") or 0)
        vals = {"crossref": crossref(doi), "opencitations": opencit(doi), "semanticscholar": s2(doi)}
        melhor = max([(v, k) for k, v in vals.items() if v is not None] or [(0, "")])
        if melhor[0] > atual:
            print(f"  {p['doi']}: {atual} -> {melhor[0]} ({melhor[1]})")
            p["citacoes"] = melhor[0]
            mudou += 1
        time.sleep(0.3)
    if mudou:
        F.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
    print(f"Concluido: {mudou} de {len(pubs)} obras com citacoes atualizadas.")


if __name__ == "__main__":
    main()