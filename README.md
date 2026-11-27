# Detekcija varoe na pčelama

[![Zaštita podataka](https://github.com/jlukaaa/digitalna-obrada-slike/actions/workflows/zastita-podataka.yml/badge.svg?branch=dev)](https://github.com/jlukaaa/digitalna-obrada-slike/actions/workflows/zastita-podataka.yml)
[![Testovi](https://github.com/jlukaaa/digitalna-obrada-slike/actions/workflows/testovi.yml/badge.svg?branch=dev)](https://github.com/jlukaaa/digitalna-obrada-slike/actions/workflows/testovi.yml)
[![Provjera koda](https://github.com/jlukaaa/digitalna-obrada-slike/actions/workflows/lint.yml/badge.svg?branch=dev)](https://github.com/jlukaaa/digitalna-obrada-slike/actions/workflows/lint.yml)

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

### Geometrijsko ujednačavanje (faza 3)

Laboratorijske slike (V1) i izrezi iz košnice u isti format: **224×224, tijelo
vertikalno, glava gore, dužina tijela 80% visine**. YOLO oznake (grinja, pčela)
se transformišu zajedno sa slikom.

```bash
# V1: folder sa images/ i labels/
python -m varoa.geometrija v1 --ulaz "<v1 folder>" --izlaz "<novi folder>" [--sablon "<V1 pčele glavom gore>"]

# košnica: izrezi iz izdvajanja (640x640) -> 224x224
python -m varoa.geometrija kosnica --ulaz "<izrezi>" --izlaz "<novi folder>"
```

V1 izlaz: `images/` (sigurno glavom gore), `provjeriti/` (nesiguran smjer glave),
`labels/` (oznake u novom kadru) i `geometrija_v1.csv` (ugao, skala, veličina grinje u px).
Pozadina ostaje kakva jeste – siva pozadina je sljedeći korak (3.4).

### Maska tijela i siva pozadina (faza 3)

Na izrezima 224×224 iz geometrije: oba izvora polaze od iste elipse očekivanog tijela.
V1 (zelena pozadina): ne-zeleno i tamnije ili obojeno, pa konveksni omotač. Košnica
(drvo je smeđe kao pčela, krila providna): GrabCut po boji u L\*a\*b\*, pa zaglađivanje.
Pozadina postaje siva `[128,128,128]` sa mekim prelazom. Maska se snima posebno, jer detektor kandidata
traži varou samo na tijelu.

```bash
python -m varoa.pozadina v1      --ulaz "<izlaz geometrije v1>"      --izlaz "<novi folder>"
python -m varoa.pozadina kosnica --ulaz "<izlaz geometrije kosnica>" --izlaz "<novi folder>"
```

Izlaz: `images/` (maska u redu), `provjeriti/` (sumnjiva maska, razlog u CSV-u),
`maske/` (255 = tijelo), `labels/` (samo V1, nepromijenjene) i `pozadina.csv`
(udio, visina i solidnost maske, a za V1 i koliko grinja je unutar maske).

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