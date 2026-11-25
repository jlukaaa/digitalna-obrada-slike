import importlib.util
import json
from pathlib import Path

import pytest

_put = Path(__file__).resolve().parents[1] / "scripts" / "provjeri_podatke.py"
_spec = importlib.util.spec_from_file_location("provjeri_podatke", _put)
provjeri = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(provjeri)


@pytest.mark.parametrize("putanja", [
    "data/raw/V1_000512.jpg", "data/neki.csv", "slika.png", "src/python/x.jpg",
    "notebooks/maska.npy", "results/graf.png", "models/resnet.pth", "x/podaci.pkl",
])
def test_zabranjeno(putanja):
    assert provjeri.problem(putanja) is not None


@pytest.mark.parametrize("putanja", [
    "data/README.md", "data/raw/.gitkeep", "docs/slike/dijagram.png",
    "results/21_mjere.csv", "src/python/varoa/izdvajanje.py", "README.md",
])
def test_dozvoljeno(putanja):
    assert provjeri.problem(putanja) is None


def test_notebook_sa_slikom(tmp_path):
    nb = {"cells": [{"cell_type": "code", "source": [], "outputs": [
        {"output_type": "display_data", "data": {"image/png": "iVBOR...", "text/plain": ["<Figure>"]}}]}]}
    f = tmp_path / "a.ipynb"
    f.write_text(json.dumps(nb))
    assert provjeri.notebook_sa_slikom(str(f))
    nb["cells"][0]["outputs"] = []
    f.write_text(json.dumps(nb))
    assert not provjeri.notebook_sa_slikom(str(f))
