"""Provjera da u repozitoriju nema zaštićenih podataka.

Isto pravilo kao ``scripts/hooks/pre-commit``, ali za CIJELI repozitorij i bez
mogućnosti zaobilaženja – pokreće se na GitHubu za svaki Pull Request.

Blokira:
- bilo šta iz ``data/`` (osim ``.gitkeep`` i ``data/README.md``)
- slike van ``docs/slike/``
- modele i nizove (.pth, .pt, .h5, .onnx, .ckpt, .npy, .npz, .pkl, ...)
- ``.mat`` i slike u ``results/`` i ``models/``
- Jupyter notebooke sa izlazima koji sadrže slike

Upotreba:  python scripts/provjeri_podatke.py      (izlaz 1 = nađen problem)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

SLIKE = re.compile(r"\.(png|jpe?g|tiff?|bmp|gif)$", re.IGNORECASE)
MODELI_NIZOVI = re.compile(r"\.(pth|pt|h5|onnx|ckpt|npy|npz|pkl|pickle|joblib)$", re.IGNORECASE)
DOZVOLJENO_U_DATA = {"data/README.md"}


def fajlovi_u_repou() -> list[str]:
    izlaz = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    return [f for f in izlaz.stdout.splitlines() if f]


def problem(putanja: str) -> str | None:
    """Razlog zašto fajl ne smije biti u repou, ili None."""
    if putanja.endswith(".gitkeep"):
        return None
    if putanja.startswith("data/") and putanja not in DOZVOLJENO_U_DATA:
        return "fajl iz data/ (dataset)"
    if putanja.startswith("models/"):
        return "fajl iz models/"
    if MODELI_NIZOVI.search(putanja):
        return "model ili niz podataka"
    if putanja.startswith("results/") and (SLIKE.search(putanja) or putanja.endswith(".mat")):
        return "slika ili .mat u results/"
    if SLIKE.search(putanja) and not putanja.startswith("docs/slike/"):
        return "slika van docs/slike/"
    return None


def notebook_sa_slikom(putanja: str) -> bool:
    """Ima li notebook izlaz sa slikom (image/png, image/jpeg...)."""
    try:
        with open(putanja, encoding="utf-8") as f:
            nb = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    for celija in nb.get("cells", []):
        for izlaz in celija.get("outputs", []):
            if any(k.startswith("image/") for k in izlaz.get("data", {})):
                return True
    return False


def main() -> int:
    nadjeno = []
    for f in fajlovi_u_repou():
        razlog = problem(f)
        if razlog is None and f.endswith(".ipynb") and notebook_sa_slikom(f):
            razlog = "notebook sa slikom u izlazima (uključi nbstripout)"
        if razlog:
            nadjeno.append((f, razlog))

    if nadjeno:
        print("❌ U repozitoriju su fajlovi koji ne smiju biti tu (zaštićeni podaci):\n")
        for f, razlog in nadjeno:
            print(f"  {f}   ← {razlog}")
        print("\nUkloni ih iz commita (git rm --cached <fajl>) i pushaj ponovo.")
        print("Ako je zaštićena slika već na GitHubu, javi timu – treba je obrisati iz historije.")
        return 1
    print("✅ Nema zaštićenih podataka u repozitoriju.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
