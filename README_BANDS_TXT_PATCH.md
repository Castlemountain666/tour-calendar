# bands.txt-korjauspaketti

Tämä muuttaa kiertuekalenterin niin, että bändejä hallitaan yhdestä helposta tiedostosta:

`data/bands.txt`

## Asenna nykyiseen GitHub-repoon

Lataa tämän zipin sisältö nykyisen repon juureen ja korvaa vanhat tiedostot:

- `.github/workflows/update-calendar.yml`
- `scripts/bands_to_artists.py`
- `data/bands.txt`
- `data/source_overrides.yml`

Vanha `data/artists.yml` saa jäädä repoon. Sitä ei tarvitse muokata käsin, koska se generoidaan jatkossa automaattisesti `bands.txt`-tiedostosta.

## Lisää bändi

Avaa GitHubissa:

`data/bands.txt`

Paina kynäkuvaketta ja lisää uusi rivi:

```text
Metallica
```

Paina `Commit changes`.

## Poista bändi

Poista rivi tai kommentoi se:

```text
# Jack White
```

## Aja päivitys heti

`Actions → Update tour calendar → Run workflow`

Muuten päivitys ajetaan automaattisesti kerran päivässä.

## Jos pelkkä bändin nimi ei löydä keikkoja

Lisää virallinen tour-sivu tiedostoon:

`data/source_overrides.yml`

Esimerkki:

```yaml
Metallica:
  - https://www.metallica.com/tour/
```

Sen jälkeen muokkaat jatkossakin normaalisti vain `data/bands.txt`-tiedostoa.
