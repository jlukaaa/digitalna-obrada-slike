"""Učitavanje i snimanje slika (radi i sa putanjama koje imaju š, č, ž...)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

EKSTENZIJE = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")


def ucitaj(putanja: str | Path) -> np.ndarray:
    """Učita sliku kao BGR uint8 (H, W, 3). Siva slika se pretvara u 3 kanala.

    ``cv2.imread`` na Windowsu ne radi sa putanjama koje imaju naša slova,
    pa se fajl čita kao bajtovi i dekodira.
    """
    podaci = np.fromfile(str(putanja), dtype=np.uint8)
    slika = cv2.imdecode(podaci, cv2.IMREAD_COLOR)
    if slika is None:
        raise OSError(f"Ne mogu pročitati sliku: {putanja}")
    return slika


def sacuvaj(putanja: str | Path, slika: np.ndarray) -> None:
    """Snimi sliku (format po ekstenziji)."""
    putanja = Path(putanja)
    ok, podaci = cv2.imencode(putanja.suffix, slika)
    if not ok:
        raise OSError(f"Ne mogu snimiti sliku: {putanja}")
    podaci.tofile(str(putanja))


def listaj(folder: str | Path) -> list[Path]:
    """Sve slike u folderu (bez podfoldera), sortirane po imenu = po vremenu."""
    folder = Path(folder)
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EKSTENZIJE)


def siva(slika_bgr: np.ndarray) -> np.ndarray:
    """BGR -> siva (float64, 0..255), iste težine kao MATLAB rgb2gray."""
    b, g, r = (slika_bgr[..., k].astype(np.float64) for k in range(3))
    return 0.2989 * r + 0.5870 * g + 0.1140 * b
