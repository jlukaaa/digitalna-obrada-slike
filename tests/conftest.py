"""Umjetne slike za testove.

Pravi dataset je zaštićen i nije na GitHubu, pa testovi crtaju svoje "pčele":
tamne izdužene elipse sa prugama na zatku, na teksturi koja liči na drvo.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from varoa import slike

VISINA, SIRINA = 1200, 1600
DUZINA_PCELE = 400          # px na "originalnoj" slici


def pozadina(seed: int = 0) -> np.ndarray:
    """Svijetlo-smeđa tekstura sa vlaknima (kao drvo)."""
    rng = np.random.default_rng(seed)
    y = np.arange(VISINA)[:, None]
    vlakna = 12 * np.sin(y / 7.0) + rng.normal(0, 4, (VISINA, SIRINA))
    baza = np.array([95, 145, 185], float)            # BGR
    return np.clip(baza + vlakna[..., None], 0, 255).astype(np.uint8)


def nacrtaj_pcelu(img: np.ndarray, cx: float, cy: float, glava_ugao: float,
                  duzina: float = DUZINA_PCELE) -> None:
    """Pčela sa centrom (cx, cy); ``glava_ugao`` = smjer glave u stepenima
    (0 = desno, 90 = gore, kao na ekranu). Zadak ima svijetle pruge."""
    sirina = 0.35 * duzina
    t = np.radians(glava_ugao)
    smjer = np.array([np.cos(t), -np.sin(t)])          # y prema dolje
    cv2.ellipse(img, (round(cx), round(cy)), (round(duzina / 2), round(sirina / 2)),
                -glava_ugao, 0, 360, (30, 35, 40), -1)
    # pruge na zatku (stražnja polovina tijela)
    for k in range(4):
        d = -0.1 * duzina - k * 0.09 * duzina
        px, py = np.array([cx, cy]) + d * smjer
        cv2.ellipse(img, (round(px), round(py)), (round(0.02 * duzina), round(0.30 * sirina)),
                    -glava_ugao, 0, 360, (55, 85, 110), -1)


def snimi(folder: Path, ime: str, img: np.ndarray) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    slike.sacuvaj(folder / ime, img)


def ime_slike(sekunde: float) -> str:
    ms = round(sekunde * 1000)
    return f"slika_T_2026-01-01_10-00-{ms // 1000:02d}-{ms % 1000:03d}.jpg"


@pytest.fixture
def opcije():
    from varoa.izdvajanje import Opcije
    return Opcije(duzina_pcele=DUZINA_PCELE, min_ostrina=0, sacuvaj_debug=False)
