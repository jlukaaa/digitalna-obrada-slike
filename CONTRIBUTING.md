# Pravila rada

## Grane

| Grana | Namjena |
|---|---|
| `main` | samo završene faze (v0.1, v0.2, ...). Ne dira se direktno. |
| `dev` | glavna radna grana. U nju ide sav rad preko Pull Requesta. |
| `<tip>/<broj-issuea>-kratki-opis` | jedan issue = jedna grana |

Primjeri: `feature/12-model-pozadine`, `fix/15-padding-na-rubu`, `docs/3-readme-contributing`.

Direktan push na `main` i `dev` je zabranjen (ruleset na GitHubu + lokalni `pre-push` hook).

## Tok rada

1. **Issue** – svaki posao počinje issueom, napravljenim iz šablona.
2. **Tabla** – kartica u `Todo`, popuniti Assignee, Estimate i datume.
3. **Grana** – u issueu desno **Development → Create a branch**, izvor `dev`.
   Lokalno:
   ```bash
   git fetch origin
   git switch <ime-grane>
   ```
   Kartica ide u `In Progress`.
4. **Rad** – mali, česti commitovi.
5. **Pull Request** prema `dev`, u opisu `Closes #<broj>`. Kartica ide u `In Review`.
6. **Review** – drugi član tima pregleda i odobri.
7. **Squash and merge** – grana se automatski briše, issue se zatvori, kartica ide u `Done`.
8. Lokalno:
   ```bash
   git switch dev
   git pull
   git branch -d <ime-grane>
   ```

## Commit poruke

Format [Conventional Commits](https://www.conventionalcommits.org/): `tip(oblast): opis`

| Tip | Kada |
|---|---|
| `feat` | nova funkcionalnost |
| `fix` | ispravka greške |
| `docs` | dokumentacija |
| `refactor` | sređivanje koda bez promjene ponašanja |
| `test` | testovi |
| `chore` | konfiguracija, alati, održavanje |
| `perf` | ubrzanje |
| `ci` | GitHub Actions |
| `release` | PR `dev → main` na kraju faze |

Primjeri:
```
feat(detection): model pozadine iz medijana uzastopnih slika
fix(normalization): pogrešan smjer glave kod pčela na rubu
docs: opis dataseta
```

## Pull Request

- Naslov u istom formatu kao commit poruka (postaje commit na `dev` nakon squasha).
- Opis prema šablonu, uvijek sa `Closes #<broj>`.
- Jedan PR = jedan issue. Veliki posao podijeliti na sub-issue.
- Merge isključivo **Squash and merge**.

## Automatske provjere (GitHub Actions)

Na svakom PR-u prema `dev` i `main` pokreću se četiri provjere. PR se može spojiti tek
kad su sve zelene.

| Provjera | Šta radi | Lokalno |
|---|---|---|
| **Zaštita podataka** | obara PR ako u repou ima slika, `data/`, modela, nizova ili notebooka sa slikama | `python scripts/provjeri_podatke.py` |
| **Provjera koda** | `ruff`: neiskorišteni importi, nedefinisana imena, sintaksa | `ruff check .` |
| **Testovi** | `pytest` na umjetnim slikama (`tests/`) | `pytest` |
| **Naslov i opis PR-a** | naslov `tip: opis`; prema `dev` u opisu `Closes #` ili `Refs #` | – |

Novi kod u `src/python/varoa/` → po mogućnosti i test u `tests/`. Testovi nikad ne koriste
prave slike – samo umjetne, nacrtane u samom testu (`tests/conftest.py`).

## Tabla (Projects)

| Kada | Šta se popunjava |
|---|---|
| Novi issue (`Backlog`) | labele, milestone |
| Prelazak u `Todo` | assignee, Estimate (sati), Start date, Target date |
| Otvoren PR | kartica u `In Review` |
| Merge | automatski `Done` |

- **Estimate**: 1, 2, 4, 8 ili 16 sati. Više od 16 → podijeliti na sub-issue.
- **Target date** nikad poslije roka milestonea.
- Na tabli su samo issue; PR se vidi u koloni *Linked pull requests*.

## Labele

| Grupa | Labele |
|---|---|
| Tip | `type: feature`, `type: bug`, `type: docs`, `type: research`, `type: chore` |
| Oblast | `area: dataset`, `area: detection`, `area: tracking`, `area: normalization`, `area: labeling`, `area: model`, `area: evaluation` |
| Jezik | `lang: matlab`, `lang: python` |
| Prioritet | `priority: high`, `priority: medium`, `priority: low` |
| Ostalo | `blocked` |

## ⚠️ Zaštićeni podaci

Repozitorij je javan, a dataset je zaštićen. Zato:

- **Nikad** ne commitovati slike iz dataseta, izreze pčela, predikcije na njima ni težine modela.
- **Nikad** ne prevlačiti slike pčela u issue, PR ili komentar – GitHub ih hostuje javno.
- Dataset se drži **van repozitorija**; putanje se podešavaju lokalno (`config_lokalno.yaml`).
- U `results/` u git ulaze samo `.csv` fajlovi sa metrikama.
- U `docs/slike/` samo vlastiti dijagrami i grafici.
- `pre-commit` hook blokira slike i fajlove iz `data/`. Ne zaobilaziti ga (`--no-verify`).

Ako zaštićeni fajl ipak završi u commitu, **ne pushati** i javiti drugom članu tima.
Ako je već pushan, javiti odmah – brisanje iz historije traži posebne korake.

## Python

Projekat se radi u Pythonu (od 23.11.2026; do tada eksperimentalno u MATLAB-u).

- Stil: [PEP 8](https://peps.python.org/pep-0008/) – funkcije i varijable `snake_case`,
  klase `PascalCase`, konstante `VELIKA_SLOVA`.
- Svaka funkcija ima docstring: šta radi, ulazi, izlazi.
- Kod koji se ponovo koristi ide u paket `src/python/varoa/` i importuje se sa
  `from varoa.<modul> import ...` (paket je instaliran sa `pip install -e .`).
- Bez apsolutnih putanja u kodu – putanje dolaze iz `ucitaj_konfiguraciju()`.
- Putanje kao `pathlib.Path`, ne kao stringovi.
- Nova biblioteka → dodati je u `requirements.txt` u istom PR-u.

## Jupyter notebooki

- Notebooki su za **eksperimente** (`notebooks/<broj-issuea>_<opis>.ipynb`).
- **nbstripout mora biti uključen** (`nbstripout --install`) – briše izlaze pri commitu.
  Notebook inače čuva prikazane slike pčela unutar `.ipynb` fajla.
- `pre-commit` hook blokira notebook u kojem je ostala slika.
- Rezultati u brojevima → `results/*.csv`; figure sa pčelama samo lokalno.
- Kad se kod iz notebooka pokaže korisnim, seli se u `src/python/varoa/`.

## Lokalni alati koji ne idu u git

Skripte za lično eksperimentisanje mogu stajati u repou, a da ih git ne vidi
i bez mijenjanja zajedničkog `.gitignore`:

```bash
echo "alati/" >> .git/info/exclude
```
