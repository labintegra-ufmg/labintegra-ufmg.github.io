#!/usr/bin/env python3
"""Recalcula h-index, obras e citacoes de cada integrante a partir das publicacoes do proprio site
(data/publicacoes/*.yaml, campo 'pesquisadores') e grava em data/equipe/stats.yaml."""
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"


def load(rel, default):
    f = D / rel
    if not f.exists():
        return default
    x = yaml.safe_load(f.read_text(encoding="utf-8"))
    return default if x is None else x


def lista(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for v in x.values():
            if isinstance(v, list):
                return v
    return []


def main():
    manual = lista(load("publicacoes/manual.yaml", []))
    auto = lista(load("publicacoes/auto.yaml", []))
    ocultas = {str(x).lower().strip() for x in lista(load("publicacoes/ocultas.yaml", []))}
    pubs = {}
    for p in manual + auto:  # manual tem prioridade
        if not isinstance(p, dict) or p.get("exemplo"):
            continue
        doi = str(p.get("doi") or "").lower().strip()
        k = doi or str(p.get("id") or "")
        if not k or k in pubs or doi in ocultas:
            continue
        pubs[k] = p

    stats = load("equipe/stats.yaml", {})
    if not isinstance(stats, dict):
        stats = {}
    ids = sorted(d.name for d in (ROOT / "content" / "equipe").iterdir() if (d / "index.md").exists())
    print(f"{'pessoa':22} obras  citacoes  h")
    for pid in ids:
        cits = sorted((int(p.get("citacoes") or 0) for p in pubs.values() if pid in (p.get("pesquisadores") or [])), reverse=True)
        h = sum(1 for i, c in enumerate(cits, 1) if c >= i)
        st = stats.setdefault(pid, {})
        st.update({"h_index": h, "obras": len(cits), "citacoes": sum(cits)})
        print(f"{pid:22} {len(cits):5}  {sum(cits):8}  {h}")
    (D / "equipe").mkdir(exist_ok=True)
    (D / "equipe" / "stats.yaml").write_text(yaml.safe_dump(stats, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print("OK: data/equipe/stats.yaml")


if __name__ == "__main__":
    main()