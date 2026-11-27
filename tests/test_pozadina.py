import csv

import cv2
import numpy as np
import pytest

from conftest import nacrtaj_pcelu, pozadina
from test_geometrija import _v1_slika
from varoa import slike
from varoa.geometrija import KLASA_VAROA, normalizuj_v1, snimi_oznake
from varoa.pozadina import Opcije, maska_tijela, obradi, zamijeni_pozadinu

SIVA = np.array([128, 128, 128])


def _istina(duzina=179, sirina_udio=0.35):
    """Maska nacrtane pčele (vertikalna, centrirana) za poređenje."""
    m = np.zeros((224, 224), np.uint8)
    cv2.ellipse(m, (112, 112), (round(duzina / 2), round(sirina_udio * duzina / 2)), -90, 0, 360, 1, -1)
    return m > 0


def _iou(a, b):
    return (a & b).sum() / (a | b).sum()


def _kosnica_izrez(susjed=True):
    """Izrez iz košnice: drvo, pčela vertikalno u centru (80% visine), dio susjedne pčele u uglu."""
    img = cv2.resize(pozadina(1)[:640, :640], (224, 224), interpolation=cv2.INTER_AREA)
    if susjed:
        nacrtaj_pcelu(img, 10, 20, 30, duzina=179)          # susjedna pčela uz rub
    nacrtaj_pcelu(img, 112, 112, 90, duzina=179)
    return img


def test_kosnica_maska_bez_susjeda_i_sa_prugama():
    img = _kosnica_izrez()
    m, info = maska_tijela(img, "kosnica")
    assert _iou(m, _istina()) > 0.85
    assert not m[:40, :40].any()                            # susjedna pčela nije u maski
    assert info["L_pozadine_prije"] > 120                   # pozadina = drvo, a ne susjed


def test_v1_iz_geometrije_grinja_u_maski():
    img, okviri = _v1_slika(90)
    izrez, novi, _ = normalizuj_v1(img, okviri)
    m, _ = maska_tijela(izrez, "v1")
    assert _iou(m, _istina()) > 0.85
    varoa = next(o for o in novi if o.klasa == KLASA_VAROA)
    assert m[round(varoa.cy), round(varoa.cx)]


def test_zamjena_pozadine():
    img = _kosnica_izrez(susjed=False)
    m, _ = maska_tijela(img, "kosnica")
    out = zamijeni_pozadinu(img, m)
    assert np.abs(out[5, 5].astype(int) - SIVA).max() <= 1          # daleko od tijela: siva
    assert np.array_equal(out[112, 112], img[112, 112])             # sredina tijela netaknuta


def test_pogresan_izvor():
    with pytest.raises(ValueError):
        maska_tijela(np.zeros((224, 224, 3), np.uint8), "lab")


def test_prazna_slika_ide_u_provjeriti(tmp_path):
    ulaz = tmp_path / "ulaz"
    ulaz.mkdir()
    slike.sacuvaj(ulaz / "prazna.png", np.full((224, 224, 3), 150, np.uint8))
    slike.sacuvaj(ulaz / "pcela.png", _kosnica_izrez())
    r = obradi(ulaz, tmp_path / "izlaz", "kosnica")
    assert r["ok"] == 1 and r["provjeriti"] == 1
    assert (tmp_path / "izlaz" / "provjeriti" / "prazna.png").exists()
    assert (tmp_path / "izlaz" / "maske" / "pcela.png").exists()


def test_v1_folder(tmp_path):
    ulaz = tmp_path / "v1_224"
    for d in ("images", "provjeriti", "labels"):
        (ulaz / d).mkdir(parents=True)
    for i, (ugao, pod) in enumerate([(90, "images"), (-90, "provjeriti")]):
        img, okviri = _v1_slika(ugao)
        izrez, novi, _ = normalizuj_v1(img, okviri)
        slike.sacuvaj(ulaz / pod / f"V1_{i}.png", izrez)
        snimi_oznake(ulaz / "labels" / f"V1_{i}.txt", novi, 224, 224)

    izlaz = tmp_path / "izlaz"
    r = obradi(ulaz, izlaz, "v1")
    assert r["ok"] == 2                                     # obje slike, bez obzira na smjer glave
    assert r["varoa_u_maski"] == r["varoa_ukupno"] == 2
    assert sorted(p.name for p in (izlaz / "labels").iterdir()) == ["V1_0.txt", "V1_1.txt"]
    with open(izlaz / "pozadina.csv", encoding="utf-8") as f:
        redovi = list(csv.DictReader(f))
    assert len(redovi) == 2 and all(r["kategorija"] == "ok" for r in redovi)
    with pytest.raises(FileExistsError):
        obradi(ulaz, izlaz, "v1")


def test_opcije_granice():
    o = Opcije()
    assert o.udio_maske[0] < _istina().mean() < o.udio_maske[1]
