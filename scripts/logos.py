#!/usr/bin/env python3
"""Baixa o logo/icone de cada parceiro de data/site/parceiros.yaml para static/images/parceiros/<id>.<ext>.
Use 'logo_url:' no yaml para forcar uma URL. Confira o resultado visualmente."""
import argparse, re
from pathlib import Path
from urllib.parse import urljoin
import requests, yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "images" / "parceiros"
H = {"User-Agent": "Mozilla/5.0 (LabIntegra-site)"}
EXTS = ("svg", "png", "jpg", "jpeg", "webp")


def attrs(tag):
    return {k.lower(): v for k, v in re.findall(r'([\w:-]+)\s*=\s*["\']([^"\']*)["\']', tag)}


def candidatos(url):
    r = requests.get(url, headers=H, timeout=30)
    r.raise_for_status()
    base, html, c = r.url, r.text, []
    for tag in re.findall(r"<link\b[^>]*>", html, re.I):
        a = attrs(tag)
        rel = a.get("rel", "").lower()
        if "icon" not in rel or not a.get("href"):
            continue
        href = urljoin(base, a["href"])
        if href.lower().split("?")[0].endswith(".svg") or "svg" in a.get("type", ""):
            pr = 0
        elif "apple" in rel:
            pr = 1
        else:
            pr = 3
        m = re.match(r"(\d+)x", a.get("sizes", ""))
        c.append((pr, -(int(m.group(1)) if m else 0), href))
    for tag in re.findall(r"<meta\b[^>]*>", html, re.I):
        a = attrs(tag)
        if a.get("property", "").lower() == "og:image" and a.get("content"):
            c.append((2, 0, urljoin(base, a["content"])))
    c.sort()
    vistos, res = set(), []
    for _, _, h in c:
        if h not in vistos:
            vistos.add(h)
            res.append(h)
    return res


def baixar(href):
    r = requests.get(href, headers=H, timeout=30)
    r.raise_for_status()
    ct, path = r.headers.get("content-type", "").lower(), href.lower().split("?")[0]
    if "svg" in ct or path.endswith(".svg"):
        ext = "svg"
    elif "png" in ct or path.endswith(".png"):
        ext = "png"
    elif "webp" in ct or path.endswith(".webp"):
        ext = "webp"
    elif "jpeg" in ct or path.endswith((".jpg", ".jpeg")):
        ext = "jpg"
    else:
        return None
    return (ext, r.content) if len(r.content) > 400 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for p in yaml.safe_load((ROOT / "data/site/parceiros.yaml").read_text(encoding="utf-8")) or []:
        pid = p["id"]
        if not a.force and any((OUT / f"{pid}.{e}").exists() for e in EXTS):
            print(f"= {pid}: ja tem logo")
            continue
        try:
            cands = [p["logo_url"]] if p.get("logo_url") else candidatos(p["url"])
        except Exception as e:
            print(f"! {pid}: site inacessivel ({e}). Coloque o arquivo manualmente.")
            continue
        for href in cands[:6]:
            try:
                got = baixar(href)
            except Exception:
                continue
            if got:
                for e in EXTS:
                    (OUT / f"{pid}.{e}").unlink(missing_ok=True)
                (OUT / f"{pid}.{got[0]}").write_bytes(got[1])
                print(f"OK {pid}: {href}")
                break
        else:
            print(f"? {pid}: nenhum logo automatico. Salve static/images/parceiros/{pid}.png")


if __name__ == "__main__":
    main()