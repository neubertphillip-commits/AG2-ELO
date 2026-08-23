# NFL Approximate Value Tracker

Nachbau der [Pro-Football-Reference Approximate-Value-Methodik](https://www.pro-football-reference.com/about/approximate_value.htm)
auf Basis kostenloser Daten (`nfl_data_py`, ein Wrapper um die
[nflverse](https://github.com/nflverse)-Datensaetze - kein API-Key noetig).

Post-Game-Update (keine In-Game-Live-Werte), mit:
- Saison-Rangliste
- Career- und Weighted-Career-AV (inkl. "AV je eingerechneter Saison")
- Laufende Saison: aktueller Stand + Hochrechnung (Pace-Projection) auf die volle Saison
- Alle "willkuerlich kalibrierten" PFR-Konstanten frei editierbar (siehe `config.py` / Sidebar)

## Starten

```bash
pip install -r requirements.txt
streamlit run nfl_av_tracker/app.py
```

Alle Rohdaten und berechneten AV-Werte landen dauerhaft in einer lokalen
SQLite-Datenbank (`nfl_av_tracker/data_cache/tracker.db`) - siehe
"Persistenz / SQLite-Cache" unten. Diese DB-Datei ist **im Repo committed**
und bereits mit den Saisons **2018-2025** vorgeladen (31 MB) - kein
Erstladen noetig, direkt einsatzbereit.

## Modulaufbau

| Datei | Zweck |
|---|---|
| `config.py` | Alle AV-Konstanten als editierbares `AVConfig`-Dataclass |
| `db.py` | SQLite-Persistenz: Rohdaten + AV-Ergebnis-Cache je Config-Hash |
| `data_source.py` | Duenne Wrapper-Schicht auf `db.py` fuer aggregate.py |
| `aggregate.py` | Rohdaten -> Boxscore-Tabellen (Team-Pools, Spieler-Stats) |
| `av_engine.py` | Die eigentlichen PFR-AV-Formeln (Offense/Defense/Special Teams) |
| `pipeline.py` | Verbindet alles zu `build_season_av()` / `build_multi_season_av()`, inkl. Cache-Logik |
| `career.py` | Weighted Career AV |
| `projection.py` | Pace-Hochrechnung fuer die laufende Saison |
| `app.py` | Streamlit-UI |

## Persistenz / SQLite-Cache

Eine einzige DB-Datei haelt zwei Arten von Daten dauerhaft vor:

1. **Rohdaten**: jede Saison wird genau einmal von nflverse geladen, egal
   wie oft man sie danach fuer verschiedene Config-Varianten braucht.
   Wo immer moeglich werden **fertige Box-Score-Tabellen** genutzt statt
   voller Play-by-Play-Daten (siehe "Box-Score statt Play-by-Play" unten) -
   das haelt die DB klein.
2. **Berechnete AV-Ergebnisse**, je `(Config-Hash, Saison)`: eine
   **abgeschlossene** Saison (Spielplan komplett) wird unter einer
   bestimmten Variablen-Konfiguration nur einmal durchgerechnet. Jede
   weitere Anfrage mit denselben Variablen ist ein reiner DB-Read (siehe
   Benchmark unten). Aendert sich auch nur eine Konstante in der Sidebar,
   entsteht ein neuer Hash -> neue Berechnung, alte Ergebnisse bleiben
   erhalten (kein Ueberschreiben, kein Datenverlust bei "zurueckstellen").

   Die **laufende Saison** (unvollstaendiger Spielplan) oder ein expliziter
   Wochenstand (`through_week` gesetzt, fuer den "Laufende Saison"-Tab) wird
   **nie** gecached, weil sich diese Werte per Definition noch aendern.

Gemessener Effekt (2023er Saison, ~2.200 Spieler):
erste Berechnung ca. 17-20s, jeder weitere Abruf derselben Config < 10ms.

**Vorladen**: Sidebar -> "Datenbank-Cache" -> "Vergangene Saisons vorladen"
laedt & rechnet einen Saisonbereich in einem Rutsch durch (bzw.
`nfl_av_tracker.warm_historical_cache(cfg, seasons)` direkt aus Python).
"Kompletten Cache loeschen" setzt alles zurueck (z.B. falls nflverse
rueckwirkend Daten korrigiert hat).

### Box-Score statt Play-by-Play

Fast alles, was die AV-Formeln brauchen, gibt es bei nflverse schon fertig
aggregiert pro Spieler und Woche - ein Play-Level-Datensatz ist dafuer nicht
noetig:

- **Offense-Yards/TDs** (Rushing/Passing/Receiving): `import_weekly_data`
- **Defense-Sacks/INTs/Tackles** (kombiniert, kein Solo/Assist-Split mehr):
  `import_weekly_pfr('def')` - **nur ab 2018 verfuegbar**
- **Snap Counts** (Games-Started-Naeherung): `import_snap_counts` - **nur
  ab 2013 verfuegbar**

Nur fuer Kicker-Distanzbaender, Punt-Laenge pro Versuch, Fumble-Recoveries
und Defensive-TDs gibt es keine Box-Score-Tabelle; dafuer wird Play-by-Play
auf genau diese Play-Typen gefiltert (`raw_pbp_special`, ca. 10% der Plays
einer vollen Saison statt 100%).

**Fallback**: Falls nflverse eine Box-Score-Datei fuer eine sonst
unterstuetzte Saison (noch) nicht veroeffentlicht hat - typischerweise kurz
nach Ende der aktuellsten Saison, bevor nflverse nachzieht - wird sie
automatisch aus vollem PBP fuer genau diese eine Saison abgeleitet (nicht
dauerhaft als PBP gespeichert, nur die abgeleitete schlanke Form). Betraf
beim Aufbau dieses Caches die Saison 2025.

Effekt: eine Saison PBP-Rest (`raw_pbp_special`) + beide Box-Score-Tabellen
+ Snap Counts + Schedules + Rosters zusammen sind ca. **4-6 MB/Saison**
(statt ~10 MB/Saison mit vollem PBP).

## Bekannte Datenluecken (wichtig!)

Freie APIs bilden PFRs proprietaer gepflegte Datenbasis nicht 1:1 ab. Das
sind die bewussten Kompromisse in diesem Tracker:

- **Games Started** gibt es ueber freie Quellen nicht direkt. Es wird ueber
  einen Snap-Anteil-Schwellenwert approximiert (Default: 50% Offense-/
  Defense-/Special-Teams-Snaps = "Start"). Einstellbar in der Config
  (`games_started_snap_threshold`). Snap-Count-Daten gibt es bei nflverse
  erst **ab 2013** - vor 2013 ist Games Started ueberall 0 (Formeln
  degradieren graceful, kein Crash, aber O-Line-/Defense-AV ist dort
  strukturell unterschaetzt).
- **Individuelle Defense-Stats** (Sacks/INTs/Tackles) kommen aus einer
  nflverse-Box-Score-Tabelle, die erst **ab 2018** existiert. Fuer Saisons
  1999-2017 sind diese Werte leer (Defense-AV basiert dort nur auf Games
  Played/Started, kein Crash, aber unvollstaendig). Der committete
  DB-Cache deckt bewusst nur 2018-2025 ab, wo die Methodik durchgaengig
  konsistent ist.
- **All-Pro-/Pro-Bowl-Ehrungen** sind ueber `nfl_data_py`/nflverse nicht
  verfuegbar (auch nicht in `import_ids`, `import_seasonal_data`,
  `import_seasonal_pfr` - alles geprueft). Recherche nach einer freien,
  aktuell gepflegten, strukturierten Quelle mit **echten Wahlen ohne
  Alternates**: keine gefunden. PFR selbst blockt automatisierte Zugriffe
  (403). Einzige frei zugaengliche Quelle sind Wikipedia-Jahresseiten
  ("20XX All-Pro Team", "List of Pro Bowl players, ..."), die Alternates
  meist in eigenen "Replacements"-Abschnitten von den echten Wahlen trennen
  - aber nur als HTML, nicht als API/CSV; muesste selbst gescraped und
  jahresweise verifiziert werden (Tabellenformat variiert ueber die
  Jahrzehnte). Der Bonus ist deshalb per Default deaktiviert
  (`enable_all_pro_bonus = False`). Die Engine akzeptiert optional ein
  `all_pro: dict[player_id, "1st"|"2nd"|"pb"]`, falls jemand eine eigene
  Liste pflegen will (z.B. aus so einem Wikipedia-Scrape).
  Nebenfund: `nflverse/nfldata`s `rosters.csv` (via `raw.githubusercontent.com/nflverse/nfldata/master/data/rosters.csv`)
  enthaelt PFRs eigene `games`/`starts`/`av`-Spalten - allerdings nur fuer
  **2006-2019** und offenbar nicht mehr gepflegt (2019 groesstenteils leer).
  Fuer die hier relevanten aktuellen/laufenden Saisons unbrauchbar, aber
  fuer 2006-2018 eine gute Referenz, um die Snap-%-Naeherung fuer "Games
  Started" gegen PFRs echte Zahlen zu validieren.
- **Tackles** sind kombinierte Solo+Assist-Zaehler aus der Box-Score-Tabelle
  (kein separater Solo/Assist-Split mehr verfuegbar) - kann punktuell von
  PFRs eigener Zaehlung abweichen.
- **Offensive-Line-Zuordnung** nutzt PFR-Spieler-IDs direkt (nicht die
  GSIS-ID-Crosswalk aus `nfl_data_py.import_ids()`), weil diese Crosswalk
  Offensive Linemen kaum abdeckt (sie ist auf Fantasy-relevante Positionen
  fokussiert).
- Play-by-Play-Daten bei nflverse beginnen **1999**, nicht 1960 wie bei PFR.

Die Formeln selbst (Team-Pools, O-Line-/Skill-Position-/Defense-Splits,
Kicker-/Punter-PAA) sind 1:1 aus der PFR-Dokumentation uebernommen - die
Naeherungen betreffen ausschliesslich Eingabedaten, die frei nicht 1:1
verfuegbar sind.
