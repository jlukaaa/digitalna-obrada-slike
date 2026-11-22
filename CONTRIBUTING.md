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
- Dataset se drži **van repozitorija**; putanje se podešavaju lokalno (issue #4).
- U `results/` u git ulaze samo `.csv` fajlovi sa metrikama.
- U `docs/slike/` samo vlastiti dijagrami i grafici.
- `pre-commit` hook blokira slike i fajlove iz `data/`. Ne zaobilaziti ga (`--no-verify`).

Ako zaštićeni fajl ipak završi u commitu, **ne pushati** i javiti drugom članu tima.
Ako je već pushan, javiti odmah – brisanje iz historije traži posebne korake.

## MATLAB

- Funkcije: `camelCase`, jedna javna funkcija po fajlu (`medianFilter.m`).
- Na vrhu svake funkcije help komentar: šta radi, ulazi, izlazi.
- Bez apsolutnih putanja u kodu – putanje dolaze iz lokalne konfiguracije.
- Parametri kao `struct` sa podrazumijevanim vrijednostima.

## Lokalni alati koji ne idu u git

Skripte za lično eksperimentisanje mogu stajati u repou, a da ih git ne vidi
i bez mijenjanja zajedničkog `.gitignore`:

```bash
echo "alati/" >> .git/info/exclude
```
