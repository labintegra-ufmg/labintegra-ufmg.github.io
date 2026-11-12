#!/usr/bin/env python3
"""ORCID (lista de obras) + OpenAlex (metadados) -> data/publicacoes/auto.yaml"""
import hashlib
import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "scripts" / "orcids.yaml"
OUT = ROOT / "data" / "publicacoes" / "auto.yaml"

MAILTO = os.getenv("OPENALEX_MAILTO", "").strip()
API_KEY = os.getenv("OPENALEX_API_KEY", "").strip()

S = requests.Session()
S.headers["User-Agent"] = "LabIntegra-site/1.0" + (f" (mailto:{MAILTO})" if MAILTO else "")

SKIP_TYPES = {"dissertation", "dissertation-thesis", "peer-review", "paratext", "erratum", "retraction"}
TYPE_MAP = {
    "article": "artigo", "journal-article": "artigo", "review": "artigo", "preprint": "artigo",
    "proceedings-article": "congresso", "conference-paper": "congresso", "conference-abstract": "congresso",
    "book-chapter": "capitulo", "book": "livro", "monograph": "livro",
}


def get(url, params=None, headers=None, tries=4):
    for k in range(tries):
        try:
            r = S.get(url, params=params, headers=headers, timeout=60)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(3 * (k + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if k == tries - 1:
                raise
            time.sleep(3 * (k + 1))
    raise RuntimeError(f"Falha ao consultar {url}")


def norm_doi(v):
    if not v:
        return ""
    v = v.strip().lower()
    v = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", v)
    return v.strip()


def orcid_works(orcid):
    data = get(f"https://pub.orcid.org/v3.0/{orcid}/works", headers={"Accept": "application/json"})
    works = []
    for g in data.get("group", []):
        doi = ""
        for e in (g.get("external-ids") or {}).get("external-id", []):
            if e.get("external-id-type") == "doi":
                doi = norm_doi(e.get("external-id-value"))
                break
        s = g["work-summary"][0]
        works.append({
            "doi": doi,
            "titulo": (((s.get("title") or {}).get("title")) or {}).get("value", ""),
            "ano": (((s.get("publication-date") or {}).get("year")) or {}).get("value", ""),
            "veiculo": ((s.get("journal-title")) or {}).get("value", ""),
            "tipo_orcid": s.get("type", ""),
        })
    return works


def openalex_by_doi(dois):
    found = {}
    dois = [d for d in dois if "," not in d]
    for i in range(0, len(dois), 40):
        batch = dois[i:i + 40]
        params = {
            "filter": "doi:" + "|".join("https://doi.org/" + d for d in batch),
            "per-page": 100,
            "select": "doi,title,authorships,publication_year,type,primary_location,open_access,cited_by_count,abstract_inverted_index",
        }
        if MAILTO:
            params["mailto"] = MAILTO
        if API_KEY:
            params["api_key"] = API_KEY
        for w in get("https://api.openalex.org/works", params=params).get("results", []):
            found[norm_doi(w.get("doi"))] = w
        time.sleep(0.3)
    return found


def abstract(inv):
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    text = " ".join(pos[i] for i in sorted(pos))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def build(work, oa, member):
    doi = work["doi"]
    rec = {}
    if oa:
        otype = oa.get("type") or ""
        if otype in SKIP_TYPES:
            return None
        rec["titulo"] = oa.get("title") or work["titulo"]
        autores = [a["author"]["display_name"] for a in oa.get("authorships", []) if a.get("author")]
        if len(autores) > 25:
            autores = autores[:25] + ["et al."]
        rec["autores"] = autores
        rec["ano"] = oa.get("publication_year") or int(work["ano"] or 0)
        rec["tipo"] = TYPE_MAP.get(otype) or TYPE_MAP.get(work["tipo_orcid"], "outro")
        src = ((oa.get("primary_location") or {}).get("source")) or {}
        rec["veiculo"] = src.get("display_name") or work["veiculo"]
        rec["acesso_aberto"] = bool((oa.get("open_access") or {}).get("is_oa"))
        oa_url = (oa.get("open_access") or {}).get("oa_url")
        if oa_url:
            rec["url_oa"] = oa_url
        rec["citacoes"] = oa.get("cited_by_count") or 0
        rec["resumo"] = abstract(oa.get("abstract_inverted_index"))
    else:
        if work["tipo_orcid"] in SKIP_TYPES:
            return None
        rec["titulo"] = work["titulo"]
        rec["autores"] = []
        rec["ano"] = int(work["ano"]) if str(work["ano"]).isdigit() else 0
        rec["tipo"] = TYPE_MAP.get(work["tipo_orcid"], "outro")
        rec["veiculo"] = work["veiculo"]
    if not rec["titulo"]:
        return None
    if doi:
        rec["id"] = "doi-" + re.sub(r"[^a-z0-9]+", "-", doi).strip("-")
        rec["doi"] = doi
    else:
        h = hashlib.sha1(f"{rec['titulo'].lower()}{rec['ano']}".encode()).hexdigest()[:10]
        rec["id"] = "orcid-" + h
    rec["pesquisadores"] = [member]
    return {k: v for k, v in rec.items() if v not in ("", None, [])}


def main():
    members = yaml.safe_load(SRC.read_text(encoding="utf-8")) or []
    merged = {}
    for m in members:
        print(f"> {m['nome']} ({m['orcid']})")
        works = orcid_works(m["orcid"])
        oa = openalex_by_doi([w["doi"] for w in works if w["doi"]])
        print(f"  {len(works)} obras no ORCID, {len(oa)} encontradas na OpenAlex")
        for w in works:
            rec = build(w, oa.get(w["doi"]), m["id"])
            if not rec:
                continue
            key = rec.get("doi") or rec["id"]
            if key in merged:
                if m["id"] not in merged[key]["pesquisadores"]:
                    merged[key]["pesquisadores"].append(m["id"])
            else:
                merged[key] = rec

    records = sorted(merged.values(), key=lambda r: (-r.get("ano", 0), r["titulo"].lower()))

    if not records and OUT.exists() and OUT.read_text(encoding="utf-8").strip() not in ("", "[]"):
        sys.exit("ERRO: resultado vazio; mantendo a base atual.")

    text = yaml.safe_dump(records, allow_unicode=True, sort_keys=False, width=100000)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"OK: {len(records)} publicações gravadas em {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()