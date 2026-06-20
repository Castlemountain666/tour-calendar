# Päivittyvä tilattava kiertuekalenteri

Tämä repo julkaisee tilattavan `calendar.ics`-kalenterin GitHub Pagesin kautta ja päivittää sen GitHub Actionsilla kerran päivässä.

Alussa mukana:
- Foo Fighters
- Def Leppard
- Jack White

## 1. Luo GitHub-repo

1. Tee GitHubissa uusi **public repository**, esim. `tour-calendar`.
2. Pura tämän zipin sisältö koneella.
3. Lataa kaikki tiedostot repon juureen.
4. Tee commit.

## 2. Laita GitHub Pages päälle

Repossa:

`Settings → Pages → Build and deployment → Source: Deploy from a branch`

Valitse:
- Branch: `main`
- Folder: `/ (root)`

Kun Pages on julkaistu, kalenterin osoite on yleensä:

`https://OMA-GITHUB-KAYTTAJANIMI.github.io/tour-calendar/calendar.ics`

Jos käytät eri reponimeä, vaihda `tour-calendar` osoitteessa sen mukaan.

## 3. Aja päivitys ensimmäisen kerran

Repossa:

`Actions → Update tour calendar → Run workflow`

Tämä luo/päivittää:
- `calendar.ics`
- `events.json`
- `index.html`
- `data/last_update.json`

## 4. Tilaa kalenteri

### iPhone / Apple Calendar

`Asetukset → Kalenteri → Tilit → Lisää tili → Muu → Lisää tilattu kalenteri`

Liitä URL:

`https://OMA-GITHUB-KAYTTAJANIMI.github.io/tour-calendar/calendar.ics`

### Google Calendar

`Other calendars → From URL`

Liitä sama URL.

## 5. Lisää tai poista artisteja

Muokkaa tiedostoa:

`data/artists.yml`

Lisää uusi artisti näin:

```yaml
- name: Metallica
  enabled: true
  sources:
    - https://www.metallica.com/tour/
```

Poista artisti joko poistamalla se tiedostosta tai vaihtamalla:

```yaml
enabled: false
```

## 6. Lisää yksittäinen tapahtuma käsin

Muokkaa tiedostoa:

`data/manual_events.yml`

Esimerkki:

```yaml
- artist: Foo Fighters
  date: 2026-07-01
  city: Berlin
  country: Germany
  venue: Olympiastadion
  url: https://foofighters.com/tour-dates/
  note: Manual event
```

## Luotettavuushuomio

Skripti yrittää lukea keikat automaattisesti lähdesivujen `schema.org` / JSON-LD -tapahtumadatasta. Kaikki artistisivut eivät tarjoa tällaista dataa, tai ne voivat olla JavaScriptillä rakennettuja. Siksi mukana on myös `data/manual_events.yml`, joka toimii varmana lähtölistana ja käsin lisättävien tapahtumien paikkana.
