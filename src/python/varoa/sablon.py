"""Šablon pčele okrenute glavom GORE i provjera smjera glave šablonom.

Šablon je prosjek izreza pčela koje su sigurno okrenute glavom gore:
smanjenih na 64x64, u sivoj skali, normalizovanih (srednja vrijednost 0,
std 1) i simetričnih lijevo-desno. Pravilno okrenuta pčela ima veću
korelaciju sa šablonom nego sa šablonom okrenutim za 180°.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from . import slike

VELICINA = 64


def pripremi(slika_bgr: np.ndarray) -> np.ndarray:
    """Izrez -> 64x64, siva skala, normalizovano (mean 0, std 1)."""
    g = slike.siva(slika_bgr) / 255.0
    faktor = g.shape[0] / VELICINA
    if faktor > 1:  # zamućenje prije smanjivanja (sprječava aliasing)
        k = 2 * int(np.ceil(faktor)) + 1
        g = cv2.GaussianBlur(g, (k, k), faktor / 2)
    g = cv2.resize(g, (VELICINA, VELICINA), interpolation=cv2.INTER_CUBIC)
    return (g - g.mean()) / max(g.std(), 1e-12)


def napravi(izvor: str | Path | Iterable[str | Path], izlaz: str | Path | None = None) -> np.ndarray:
    """Napravi šablon iz foldera, liste fajlova ili učita snimljeni ``.npy``.

    ``izvor`` – folder sa izrezima glavom gore, lista putanja, ili ``.npy`` fajl.
    ``izlaz`` – ako je zadan, šablon se snimi kao ``.npy``.
    """
    if isinstance(izvor, (str, Path)) and Path(izvor).suffix.lower() == ".npy":
        return np.load(izvor)

    if isinstance(izvor, (str, Path)):
        folder = Path(izvor)
        if not folder.is_dir():
            raise FileNotFoundError(
                f"Folder za šablon ne postoji:\n  {folder}\n"
                f"Provjeri putanju do foldera sa ručno izabranim pčelama."
            )
        fajlovi = slike.listaj(folder)
        if not fajlovi:
            raise FileNotFoundError(f"U folderu za šablon nema slika:\n  {folder}")
    else:
        fajlovi = [Path(f) for f in izvor]
        if not fajlovi:
            raise ValueError("Nema slika za šablon.")

    zbir = np.zeros((VELICINA, VELICINA))
    for f in fajlovi:
        zbir += pripremi(slike.ucitaj(f))
    if len(fajlovi) < 10:
        print(f"⚠️ Šablon od samo {len(fajlovi)} slika; preporuka je 20-30.")

    t = zbir / len(fajlovi)
    t = (t + np.fliplr(t)) / 2  # lijevo-desno simetrija
    t = (t - t.mean()) / max(t.std(), 1e-12)
    print(f"Šablon napravljen od {len(fajlovi)} slika.")
    if izlaz is not None:
        np.save(izlaz, t)
        print(f"Šablon snimljen: {izlaz}")
    return t


def provjeri_smjer(izrez_bgr: np.ndarray, sablon: np.ndarray) -> tuple[bool, float]:
    """Vrati (je_naopako, pouzdanost 0..1) za izrez koji treba biti glavom gore."""
    z = pripremi(izrez_bgr)
    c_gore = float(np.mean(z * sablon))
    c_dolje = float(np.mean(z * np.rot90(sablon, 2)))
    pouzdanost = abs(c_gore - c_dolje) / max(abs(c_gore) + abs(c_dolje), 1e-12)
    return c_dolje > c_gore, pouzdanost
