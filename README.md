# Detekcija varoe na pčelama

Projekat iz predmeta **Digitalna obrada slike**.

Cilj je automatski prepoznati pčele zaražene grinjom *Varroa destructor* na slikama
iz košnice, kombinacijom klasične obrade slike i neuronske mreže.

## Ideja

Neuronska mreža se trenira na laboratorijskim slikama pčela, a koristi se na slikama
iz fiksnih kamera u košnici, koje izgledaju potpuno drugačije (pozadina, svjetlo,
oštrina, veličina). Glavni zadatak predobrade je da te dvije vrste slika učini
**što sličnijim**, kako bi mreža učila varou, a ne razlike između domena.

```
Slika iz košnice (3 slike/s)
   │
   ▼
[1] Detekcija pčela        model pozadine, segmentacija, filtriranje
   │
   ▼
[2] Praćenje               ista pčela kroz uzastopne slike
   │
   ▼
[3] Normalizacija          glava gore, ista veličina, siva pozadina, boja
   │
   ▼
[4] Klasifikator (CNN)     varoa / nema vidljive varoe
   │
   ▼
[5] Odluka po pčeli        objedinjavanje kroz više slika iste pčele
```


## Struktura repozitorija

| Folder | Sadržaj |
|---|---|
| `src/python/varoa/` | Python paket projekta (kod koji se ponovo koristi) |
| `notebooks/` | Jupyter notebooki za eksperimente (bez izlaza – vidi `notebooks/README.md`) |
| `tests/` | testovi |
| `docs/` | dokumentacija i izvještaj |
| `docs/slike/` | **samo** vlastiti dijagrami i grafici (bez slika iz dataseta) |
| `scripts/hooks/` | git hookovi (zaštita podataka, zaštita grana) |
| `data/` | prazno u repou; lokalno se tu može držati dataset (ignorisano) |
| `results/` | prazno u repou; dozvoljeni su samo `.csv` fajlovi sa metrikama |

## ⚠️ Podaci

Dataset sadrži **zaštićene slike** i **ne nalazi se u ovom repozitoriju**, niti smije
biti dodan, ni preko Git LFS-a, ni kao prilog u issueu ili Pull Requestu.

| Skup | Opis | Namjena |
|---|---|---|
| Laboratorija V1 | ~700 slika, zelena pozadina, pčele sa varoom | trening (pozitivni primjeri) |
| Košnica | fiksne kamere, 3 slike/s, drvena pozadina | trening (negativni) i test |

Detaljan opis: `docs/dataset.md`. Gdje se dataset nabavlja: `data/README.md`.

## Jednokratno podešavanje

Potrebno: **Python 3.10+**, Git, Git LFS. Preporuka: VS Code sa ekstenzijama *Python* i *Jupyter*.

```bash
git clone git@github.com:jlukaaa/digitalna-obrada-slike.git
cd digitalna-obrada-slike
git lfs install
git config core.hooksPath scripts/hooks

python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash); Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
nbstripout --install
```

- Hookovi blokiraju commit slika, nizova (`.npy`, `.pkl`...) i fajlova iz `data/`,
  notebooka sa slikama u izlazima, kao i direktan push na `main` i `dev`.
- `nbstripout` briše izlaze notebooka pri commitu – **obavezno**, jer notebook
  čuva prikazane slike pčela unutar `.ipynb` fajla.
- Okruženje se aktivira u svakom novom terminalu: `source .venv/Scripts/activate`.

## Pokretanje

### Lokalna konfiguracija (jednom)

Putanje do dataseta su različite na svakom računaru, pa se drže u lokalnom fajlu
koji ne ide u git.

1. Kopiraj `config_primjer.yaml` u `config_lokalno.yaml` (oba u korijenu repoa)
2. Upiši svoje putanje – dataset i izlazi moraju biti **van repozitorija**

U kodu (i u notebookima):
```python
from varoa.konfiguracija import ucitaj_konfiguraciju

cfg = ucitaj_konfiguraciju()
slike = sorted((cfg["putanje"]["lab_v1"] / "images" / "train").glob("V1_*.jpg"))
```

`ucitaj_konfiguraciju` javlja grešku ako fajl ili folder sa datasetom ne postoji,
pravi izlazne foldere ako ih nema i upozorava ako je izlaz unutar repoa.

### Izdvajanje pčela iz slika košnice (faza 2)

Iz slika fiksne kamere izdvaja pojedinačne pčele, okreće ih glavom gore i
razvrstava po kvalitetu. Ulaz je `putanje.kosnica` (podfolder po danu),
izlaz `putanje.predobrada`.

```bash
# svi dani; --sablon = folder sa 20-30 pčela sigurno okrenutih glavom gore
python -m varoa.predobrada --sablon "<folder sa šablonom>"

# statistika jednog dana (kategorije, dužina, oštrina) + histogrami analiza.png
python -m varoa.analiza "<predobrada>/<dan>_2"

# najbolji izrezi svake pčele iz svih dana u jedan folder
python -m varoa.izbor --izlaz "<novi folder>" --max-po-tragu 4 --razmak 3
```

Za svaki dan nastaju `<dan>/` (prvi prolaz) i `<dan>_2/` (konačno: drugi prolaz
sa šablonom napravljenim iz kretanja pčela). U `<dan>_2/`:

| Folder / fajl | Sadržaj |
|---|---|
| `pcele/` | dobri izrezi, glava gore |
| `provjeriti/` | nesiguran smjer glave |
| `mutne/` | zamućenje od pokreta |
| `spojene/` | više pčela u jednoj maski |
| `pcele_ispravljeno.csv` | podaci o svakom izrezu + trag (ista pčela kroz vrijeme) i izvor smjera glave |

Parametri (podešeni za kameru C): `varoa.izdvajanje.Opcije`.

## Kako radimo

Pravila rada (grane, commitovi, Pull Requestovi, tabla): [CONTRIBUTING.md](CONTRIBUTING.md).

Napredak se prati na [Projects tabli](https://github.com/users/jlukaaa/projects) po fazama:

| # | Faza (milestone) | Release |
|---|---|---|
| 1 | Priprema projekta i analiza podataka | `v0.1` |
| 2 | Izdvajanje pčela iz slika košnice | `v0.2` |
| 3 | Ujednačavanje slika iz laboratorije i košnice | `v0.3` |
| 4 | Priprema skupova za učenje | `v0.4` |
| 5 | Klasifikator | `v0.5` |
| 6 | Evaluacija i analiza | `v0.6` |
| 7 | Izvještaj i prezentacija | `v1.0` |

Opis svake faze (zadatak, rezultat, kada je gotova) je u opisu milestonea na GitHubu.