import cv2
import numpy as np
import pytest

from conftest import nacrtaj_pcelu
from varoa.geometrija import (KLASA_PCELA, KLASA_VAROA, Okvir, normalizuj_v1,
                              obradi_kosnicu, putanja_oznake)
from varoa import slike


def _v1_slika(glava_ugao, varoa_d=-0.3):
    """Umjetna V1 slika 150x300: zelena pozadina, pčela, crvena 'grinja' na zatku."""
    img = np.full((300, 150, 3), (150, 225, 160), np.uint8)
    duzina = 222
    nacrtaj_pcelu(img, 75, 150, glava_ugao, duzina=duzina)
    t = np.radians(glava_ugao)
    smjer = np.array([np.cos(t), -np.sin(t)])
    vx, vy = np.array([75, 150]) + varoa_d * duzina * smjer
    cv2.circle(img, (round(vx), round(vy)), 12, (40, 40, 200), -1)
    okviri = [Okvir(KLASA_VAROA, vx, vy, 26, 26), Okvir(KLASA_PCELA, 75, 150, 150, 240)]
    return img, okviri


@pytest.mark.parametrize("glava_ugao", [90, -90, 80, -100])
def test_v1_glava_gore_i_grinja_prati_sliku(glava_ugao):
    img, okviri = _v1_slika(glava_ugao)
    izrez, novi, info = normalizuj_v1(img, okviri)

    assert izrez.shape == (224, 224, 3)
    assert abs(info["duzina_tijela_px"] - 0.8 * 224) < 8          # tijelo 80% visine
    varoa = next(o for o in novi if o.klasa == KLASA_VAROA)
    assert varoa.cy > 112                                         # grinja je na zatku -> donja polovina
    b, g, r = izrez[round(varoa.cy), round(varoa.cx)].astype(int)
    assert r > g + 60 and r > b + 60                              # okvir je stvarno na crvenoj grinji
    assert info["varoa_na_tijelu"]


def test_putanja_oznake(tmp_path):
    assert putanja_oznake(tmp_path / "images" / "train" / "V1_1.jpg") == tmp_path / "labels" / "train" / "V1_1.txt"
    assert putanja_oznake(tmp_path / "images" / "V1_1.png") == tmp_path / "labels" / "V1_1.txt"


def test_kosnica_na_224(tmp_path):
    (tmp_path / "ulaz").mkdir()
    slike.sacuvaj(tmp_path / "ulaz" / "a.png", np.zeros((640, 640, 3), np.uint8))
    obradi_kosnicu(tmp_path / "ulaz", tmp_path / "izlaz")
    assert slike.ucitaj(tmp_path / "izlaz" / "a.png").shape == (224, 224, 3)
