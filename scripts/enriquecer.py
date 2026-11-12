#!/usr/bin/env python3
"""Enriquece perfis: OpenAlex (estatisticas, temas, Scopus) + ORCID (formacao, vinculos).
  python scripts/enriquecer.py            -> atualiza data/equipe/stats.yaml
  python scripts/enriquecer.py --perfil   -> idem + completa areas/scopus vazios nos perfis
  python scripts/enriquecer.py --scopus ID --nome "Nome"   -> so consulta (conferir uma pessoa)"""
import argparse
import os
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
MAILTO = os.getenv("OPENALEX_MAILTO", "").strip()
KEY = os.getenv("OPENALEX_API_KEY", "").strip()
S = requests.Session()
S.headers["User-Agent"] = "LabIntegra-site/1.0" + (f" (mailto:{MAILTO})" if MAILTO else "")


def api(path, **params):
    if MAILTO:
        params["mailto"] = MAILTO
    if KEY:
        params["api_key"] = KEY
    r = S.get("https://api.openalex.org" + path, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def find(m):
    try:
        if m.get("openalex"):
            return api("/authors/" + m["openalex"])
        if m.get("orcid"):
            r = api("/authors", filter="orcid:https://orcid.org/" + m["orcid"]).get("results", [])
            if r:
                return r[0]
        if m.get("scopus"):
            r = api("/authors", filter="scopus:" + str(m["scopus"])).get("results", [])
            if r:
                return r[0]
    except requests.RequestException as e:
        print("  erro na OpenAlex:", e)
    return None


def resumo(a):
    ss = a.get("summary_stats") or {}
    lk = a.get("last_known_institutions") or ([a["last_known_institution"]] if a.get("last_known_institution") else [])
    sc = (a.get("ids") or {}).get("scopus") or ""
    return {
        "openalex": a["id"].split("/")[-1],
        "h_index": ss.get("h_index", 0),
        "obras": a.get("works_count", 0),
        "citacoes": a.get("cited_by_count", 0),
        "instituicoes": [i.get("display_name") for i in lk if i],
        "areas": [t["display_name"] for t in (a.get("topics") or [])[:6]],
        "scopus": sc.split("authorId=")[-1] if sc else "",
        "orcid": (a.get("orcid") or "").replace("https://orcid.org/", ""),
    }


def mostrar(a):
    s = resumo(a)
    print(f"{s['openalex']}  {a['display_name']}  | obras {s['obras']}, h-index {s['h_index']}, citacoes {s['citacoes']}")
    print("   instituicoes:", "; ".join(s["instituicoes"]) or "-")
    print("   temas:", "; ".join(s["areas"]) or "-")
    print("   scopus:", s["scopus"] or "-", "| orcid:", s["orcid"] or "-")


def orcid_lista(orcid, tipo):
    try:
        r = S.get(f"https://pub.orcid.org/v3.0/{orcid}/{tipo}", headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        d = r.json()
    except Exception:
        return []
    out = []
    for g in d.get("affiliation-group", []):
        for s in g.get("summaries", []):
            x = s.get("employment-summary") or s.get("education-summary") or {}
            org = (x.get("organization") or {}).get("name", "")
            role = x.get("role-title") or x.get("department-name") or ""
            ini = (((x.get("start-date") or {}).get("year")) or {}).get("value", "")
            fim = (((x.get("end-date") or {}).get("year")) or {}).get("value", "")
            if org:
                txt = ", ".join(filter(None, [role, org]))
                if ini:
                    txt += f" ({ini}\u2013{fim})"
                out.append(txt)
    return out


def patch_fm(pid, novos):
    for nome in ("index.md", "index.en.md"):
        f = ROOT / "content" / "equipe" / pid / nome
        if not f.exists():
            continue
        t = f.read_text(encoding="utf-8")
        if not t.startswith("---\n"):
            continue
        fim = t.index("\n---", 4)
        fm = yaml.safe_load(t[4:fim]) or {}
        mudou = False
        for k, v in novos.items():
            if v and not fm.get(k):
                fm[k] = v
                mudou = True
        if mudou:
            corpo = t[fim + 4:]
            f.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---" + corpo,
                         encoding="utf-8", newline="\n")
            print(f"  perfil atualizado: {f.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--perfil", action="store_true")
    ap.add_argument("--scopus", default="")
    ap.add_argument("--nome", default="")
    o = ap.parse_args()

    if o.scopus or o.nome:
        cands = []
        if o.scopus:
            try:
                cands = api("/authors", filter="scopus:" + o.scopus).get("results", [])
            except requests.RequestException as e:
                print("Filtro por Scopus falhou:", e)
        if not cands and o.nome:
            print("Busca por nome (confira instituicao e obras):")
            cands = api("/authors", **{"filter": "display_name.search:" + o.nome, "per-page": 8}).get("results", [])
        for a in cands:
            mostrar(a)
            print()
        if not cands:
            print("Nada encontrado.")
        return

    membros = yaml.safe_load((ROOT / "scripts" / "orcids.yaml").read_text(encoding="utf-8")) or []
    stats = {}
    for m in membros:
        print(f"> {m['nome']}")
        a = find(m)
        if not a:
            print("  sem registro na OpenAlex")
            continue
        s = resumo(a)
        e = {"openalex": s["openalex"], "h_index": s["h_index"], "obras": s["obras"], "citacoes": s["citacoes"]}
        if m.get("orcid"):
            e["formacao"] = orcid_lista(m["orcid"], "educations")
            e["vinculos"] = orcid_lista(m["orcid"], "employments")
        stats[m["id"]] = {k: v for k, v in e.items() if v not in ("", None, [])}
        if o.perfil:
            patch_fm(m["id"], {"areas": s["areas"], "scopus": str(m.get("scopus") or s["scopus"])})
        time.sleep(0.3)
    if not stats:
        sys.exit("Nada obtido; mantendo stats.yaml atual.")
    out = ROOT / "data" / "equipe" / "stats.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(stats, allow_unicode=True, sort_keys=False, width=100000), encoding="utf-8", newline="\n")
    print(f"OK: {len(stats)} perfis em {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()