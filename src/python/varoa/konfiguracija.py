"""Učitavanje lokalnih putanja iz ``config_lokalno.yaml``.

Primjer::

    from varoa.konfiguracija import ucitaj_konfiguraciju

    cfg = ucitaj_konfiguraciju()
    slike = sorted((cfg["putanje"]["lab_v1"] / "images" / "train").glob("V1_*.jpg"))
"""

from __future__ import annotations

import warnings
from pathlib import Path

import yaml

KORIJEN_REPOA = Path(__file__).resolve().parents[3]
LOKALNI_FAJL = KORIJEN_REPOA / "config_lokalno.yaml"
SABLON_FAJL = KORIJEN_REPOA / "config_primjer.yaml"

ULAZI = ("lab_v1", "kosnica")
IZLAZI = ("predobrada", "modeli", "rezultati")


class GreskaKonfiguracije(RuntimeError):
    """Lokalna konfiguracija nedostaje ili nije ispravna."""


def ucitaj_konfiguraciju(napravi_izlaze: bool = True, fajl: Path | None = None) -> dict:
    """Učita ``config_lokalno.yaml`` i provjeri putanje.

    - ulazni folderi (dataset) moraju postojati
    - izlazni folderi se prave ako ne postoje (osim ako je ``napravi_izlaze=False``)
    - upozorava ako je neki izlaz unutar repozitorija

    Vraća rječnik u kojem su sve putanje ``pathlib.Path``.
    """
    fajl = Path(fajl) if fajl else LOKALNI_FAJL
    if not fajl.exists():
        raise GreskaKonfiguracije(
            f"Nema lokalne konfiguracije: {fajl}\n"
            f"  1. Kopiraj {SABLON_FAJL.name} u {LOKALNI_FAJL.name} (korijen repoa)\n"
            f"  2. Upiši svoje putanje do dataseta"
        )

    with open(fajl, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    putanje = cfg.get("putanje") or {}
    for kljuc in ULAZI + IZLAZI:
        if not putanje.get(kljuc):
            raise GreskaKonfiguracije(
                f"U {fajl.name} nedostaje putanje.{kljuc} (vidi {SABLON_FAJL.name})."
            )
        putanje[kljuc] = Path(putanje[kljuc]).expanduser()

    for kljuc in ULAZI:
        if not putanje[kljuc].is_dir():
            raise GreskaKonfiguracije(
                f"Folder za putanje.{kljuc} ne postoji:\n  {putanje[kljuc]}"
            )

    for kljuc in IZLAZI:
        p = putanje[kljuc]
        if napravi_izlaze and not p.exists():
            p.mkdir(parents=True)
            print(f"Napravljen folder: {p}")
        if _je_unutar(p, KORIJEN_REPOA):
            warnings.warn(
                f"putanje.{kljuc} je unutar repozitorija. Izlazi sadrže zaštićene "
                f"slike – premjesti ih van repoa.",
                stacklevel=2,
            )

    cfg["putanje"] = putanje
    return cfg


def _je_unutar(putanja: Path, korijen: Path) -> bool:
    try:
        putanja.resolve().relative_to(korijen.resolve())
        return True
    except ValueError:
        return False
