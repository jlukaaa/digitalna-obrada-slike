import pytest

from varoa.konfiguracija import GreskaKonfiguracije, ucitaj_konfiguraciju


def _yaml(tmp_path, lab_v1):
    f = tmp_path / "config_lokalno.yaml"
    f.write_text(
        "putanje:\n"
        f"  lab_v1: '{lab_v1}'\n"
        f"  kosnica: '{tmp_path / 'kosnica'}'\n"
        f"  predobrada: '{tmp_path / 'izlaz' / 'predobrada'}'\n"
        f"  modeli: '{tmp_path / 'izlaz' / 'modeli'}'\n"
        f"  rezultati: '{tmp_path / 'izlaz' / 'rezultati'}'\n",
        encoding="utf-8",
    )
    return f


def test_nema_fajla(tmp_path):
    with pytest.raises(GreskaKonfiguracije, match="Nema lokalne konfiguracije"):
        ucitaj_konfiguraciju(fajl=tmp_path / "nema.yaml")


def test_nepostojeci_dataset(tmp_path):
    (tmp_path / "kosnica").mkdir()
    with pytest.raises(GreskaKonfiguracije, match="lab_v1 ne postoji"):
        ucitaj_konfiguraciju(fajl=_yaml(tmp_path, tmp_path / "nema"))


def test_ispravna_konfiguracija_pravi_izlaze(tmp_path):
    (tmp_path / "lab").mkdir()
    (tmp_path / "kosnica").mkdir()
    cfg = ucitaj_konfiguraciju(fajl=_yaml(tmp_path, tmp_path / "lab"))
    for kljuc in ("predobrada", "modeli", "rezultati"):
        assert cfg["putanje"][kljuc].is_dir()
