"""Izbor izreza za eksperimente: najbolji izrez(i) svake pčele, iz više dana."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from .pracenje import vrijeme_iz_imena


def izaberi_po_tragu(korijen_izlaz: str | Path, izlazni_folder: str | Path,
                     cilj_broj: int = 1400, max_po_tragu: int = 1,
                     min_razmak: float = 3.0) -> pd.DataFrame:
    """Skupi najoštrije izreze svake pčele iz svih ``<dan>_2`` foldera u jedan folder.

    - samo izrezi iz ``pcele/`` (kategorija ok); fajlovi kojih nema se preskaču
    - iz svakog traga (iste pčele) najviše ``max_po_tragu`` izreza, razmaknutih
      bar ``min_razmak`` sekundi (različiti položaji)
    - redoslijed: prvo po jedan izrez SVAKE pčele, pa drugi, ... (raznolikost)
    - podjednako iz svakog dana (kružno), najoštriji prvi

    Izlaz: ``<izlazni_folder>/<dan>__<izrez>.png`` i ``izabrane.csv``.
    """
    korijen_izlaz, izlazni_folder = Path(korijen_izlaz), Path(izlazni_folder)
    if izlazni_folder.exists() and any(izlazni_folder.glob("*.png")):
        raise FileExistsError(f'Izlazni folder "{izlazni_folder}" nije prazan.')
    izlazni_folder.mkdir(parents=True, exist_ok=True)

    dani = sorted(p for p in korijen_izlaz.iterdir() if p.is_dir() and p.name.endswith("_2"))
    if not dani:
        raise FileNotFoundError(f'U "{korijen_izlaz}" nema foldera koji završavaju sa _2.')

    kandidati = []
    for folder in dani:
        t = pd.read_csv(folder / "pcele_ispravljeno.csv")
        t = t[t["kategorija"] == "ok"].copy()
        postoji = t["izrez"].map(lambda f: (folder / "pcele" / f).exists())
        nema = int((~postoji).sum())
        t = t[postoji]
        # pčele bez traga (trag 0) su svaka za sebe
        bez = t["trag"] == 0
        t.loc[bez, "trag"] = -np.arange(1, bez.sum() + 1)
        t["vrijeme"] = t["izvor"].map(vrijeme_iz_imena)

        izabrani = []
        for _, grupa in t.groupby("trag"):
            uzeti = []
            for _, red in grupa.sort_values("ostrina", ascending=False).iterrows():
                if len(uzeti) >= max_po_tragu:
                    break
                if all(abs(red["vrijeme"] - u["vrijeme"]) >= min_razmak or np.isnan(red["vrijeme"])
                       for u in uzeti):
                    uzeti.append(red)
            for rang, red in enumerate(uzeti, start=1):
                izabrani.append({**red.to_dict(), "rang_u_tragu": rang})
        k = pd.DataFrame(izabrani).sort_values(["rang_u_tragu", "ostrina"], ascending=[True, False])
        k["dan"] = folder.name.removesuffix("_2")
        k["folder"] = str(folder)
        kandidati.append(k.reset_index(drop=True))
        if nema:
            print(f"  ({folder.name}: {nema} izreza iz CSV-a nema u pcele/, preskočeni)")
        print(f"{folder.name:<20} {len(t):4d} izreza u pcele/, {t['trag'].nunique():4d} "
              f"različitih pčela, {len(k):4d} kandidata")

    # podjednako iz svakog dana (kružno)
    izbor, pozicija = [], [0] * len(kandidati)
    while len(izbor) < cilj_broj:
        dodano = False
        for j, k in enumerate(kandidati):
            if pozicija[j] < len(k) and len(izbor) < cilj_broj:
                izbor.append(k.iloc[pozicija[j]])
                pozicija[j] += 1
                dodano = True
        if not dodano:
            break

    redovi = []
    for red in izbor:
        novo_ime = f"{red['dan']}__{red['izrez']}"
        shutil.copy2(Path(red["folder"]) / "pcele" / red["izrez"], izlazni_folder / novo_ime)
        redovi.append({"slika": novo_ime, "dan": red["dan"], "izvorni_izrez": red["izrez"],
                       "trag": int(red["trag"]), "rang_u_tragu": int(red["rang_u_tragu"]),
                       "ostrina": round(float(red["ostrina"]), 1)})
    rezultat = pd.DataFrame(redovi)
    rezultat.to_csv(izlazni_folder / "izabrane.csv", index=False)

    print(f"\nKopirano {len(rezultat)} izreza u {izlazni_folder}")
    if len(rezultat):
        for dan, broj in rezultat["dan"].value_counts().sort_index().items():
            print(f"  {dan:<20} {broj}")
    if len(rezultat) < cilj_broj:
        print(f"⚠️ Fali {cilj_broj - len(rezultat)} do {cilj_broj}. Povećaj max_po_tragu, "
              f"dodaj snimka ili radi sa {len(rezultat)} parova.")
    return rezultat


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(
        prog="python -m varoa.izbor",
        description="Skupi najbolje izreze svake pčele iz svih <dan>_2 foldera u jedan folder.")
    p.add_argument("--izlaz", required=True, help="novi (prazan) folder za izabrane izreze")
    p.add_argument("--korijen", help="folder sa <dan>_2 folderima (podrazumijevano: putanje.predobrada)")
    p.add_argument("--cilj", type=int, default=1400, help="koliko izreza ukupno")
    p.add_argument("--max-po-tragu", type=int, default=1, help="najviše izreza iste pčele")
    p.add_argument("--razmak", type=float, default=3.0, help="min. razmak (s) između izreza iste pčele")
    a = p.parse_args(argv)
    if a.korijen:
        korijen = Path(a.korijen)
    else:
        from .konfiguracija import ucitaj_konfiguraciju
        korijen = ucitaj_konfiguraciju()["putanje"]["predobrada"]
    izaberi_po_tragu(korijen, a.izlaz, a.cilj, a.max_po_tragu, a.razmak)


if __name__ == "__main__":
    main()
