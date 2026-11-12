#!/usr/bin/env python3
"""Le fotos de fotos/, casa com os perfis de content/equipe pelo nome e grava
static/images/equipe/<id>.jpg (quadrado, 480 px)."""
import argparse, re, unicodedata
from pathlib import Path
import yaml
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
IN, OUT, EQ = ROOT / "fotos", ROOT / "static" / "images" / "equipe", ROOT / "content" / "equipe"
EXT = {".jpg", ".jpeg", ".png", ".webp"}
STOP = {"de", "da", "do", "dos", "das", "e", "foto", "fotografia", "perfil", "photo", "img", "copy", "copia"}


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return [t for t in re.split(r"[^a-z0-9]+", s) if t and t not in STOP and not t.isdigit()]


def pessoas():
    res = {}
    for d in sorted(EQ.iterdir()):
        md = d / "index.md"
        if not (d.is_dir() and md.exists()):
            continue
        m = re.match(r"^---\s*\n(.*?)\n---", md.read_text(encoding="utf-8"), re.S)
        fm = (yaml.safe_load(m.group(1)) if m else {}) or {}
        titulo = fm.get("title") or fm.get("nome") or d.name
        res[d.name] = {"titulo": titulo, "tokens": set(norm(titulo)) | set(norm(d.name))}
    return res


def casar(stem, ps):
    ft = set(norm(stem))
    if not ft:
        return None, []
    for pid in ps:  # id exato
        if norm(stem) == norm(pid):
            return pid, []
    cand = [(len(ft), pid) for pid, p in ps.items() if ft <= p["tokens"]]
    if not cand:
        return None, []
    best = max(s for s, _ in cand)
    top = [pid for s, pid in cand if s == best]
    return (top[0], []) if len(top) == 1 else (None, top)


def processar(src, dst, topo, size=480):
    im = ImageOps.exif_transpose(Image.open(src))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    w, h = im.size
    s = min(w, h)
    left = (w - s) // 2
    top = int((h - s) * topo) if h > w else 0
    im = im.crop((left, top, left + s, top + s))
    if s > size:
        im = im.resize((size, size), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "JPEG", quality=85, optimize=True, progressive=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="reprocessa mesmo se ja existir")
    ap.add_argument("--topo", type=float, default=0.18, help="0=corta pelo topo, 0.5=centro (fotos em pe)")
    a = ap.parse_args()
    IN.mkdir(exist_ok=True)
    ps = pessoas()
    feitas = 0
    for f in sorted(IN.iterdir()):
        if f.suffix.lower() not in EXT:
            continue
        pid, amb = casar(f.stem, ps)
        if amb:
            print(f"  ? {f.name}: ambiguo entre {', '.join(amb)} (renomeie com mais do nome)")
            continue
        if not pid:
            print(f"  ? {f.name}: nenhum perfil casa (ids: {', '.join(ps)})")
            continue
        dst = OUT / f"{pid}.jpg"
        if dst.exists() and dst.stat().st_mtime >= f.stat().st_mtime and not a.force:
            print(f"  = {f.name} -> {pid} (ja processada)")
            continue
        try:
            processar(f, dst, a.topo)
            print(f"  OK {f.name} -> static/images/equipe/{pid}.jpg")
            feitas += 1
        except Exception as e:
            print(f"  ! {f.name}: {e}")
    sem = [p for p in ps if not any((OUT / f"{p}.{e}").exists() for e in ("jpg", "jpeg", "png", "webp"))]
    print(f"\nConcluido: {feitas} foto(s) nova(s).")
    if sem:
        print("Perfis sem foto: " + ", ".join(sem))


if __name__ == "__main__":
    main()