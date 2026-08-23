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

Der erste Aufruf pro Saison laedt Play-by-Play-/Snap-Count-/Schedule-Daten
von den nflverse-GitHub-Releases (kann 10-30s dauern) und cached sie lokal
unter `nfl_av_tracker/data_cache/*.parquet`. `data_source.clear_cache()`
loescht den Cache (z.B. wenn nflverse rueckwirkend Daten korrigiert hat).

## Modulaufbau

| Datei | Zweck |
|---|---|
| `config.py` | Alle AV-Konstanten als editierbares `AVConfig`-Dataclass |
| `data_source.py` | Laden & Cachen der nflverse-Rohdaten |
| `aggregate.py` | Rohdaten -> Boxscore-Tabellen (Team-Pools, Spieler-Stats) |
| `av_engine.py` | Die eigentlichen PFR-AV-Formeln (Offense/Defense/Special Teams) |
| `pipeline.py` | Verbindet alles zu `build_season_av()` / `build_multi_season_av()` |
| `career.py` | Weighted Career AV |
| `projection.py` | Pace-Hochrechnung fuer die laufende Saison |
| `app.py` | Streamlit-UI |

## Bekannte Datenluecken (wichtig!)

Freie APIs bilden PFRs proprietaer gepflegte Datenbasis nicht 1:1 ab. Das
sind die bewussten Kompromisse in diesem Tracker:

- **Games Started** gibt es ueber freie Quellen nicht direkt. Es wird ueber
  einen Snap-Anteil-Schwellenwert approximiert (Default: 50% Offense-/
  Defense-/Special-Teams-Snaps = "Start"). Einstellbar in der Config
  (`games_started_snap_threshold`).
- **All-Pro-/Pro-Bowl-Ehrungen** sind ueber `nfl_data_py` nicht verfuegbar.
  Der entsprechende Bonus ist per Default deaktiviert (`enable_all_pro_bonus
  = False`). Die Engine akzeptiert optional ein `all_pro: dict[player_id,
  "1st"|"2nd"|"pb"]`, falls jemand eine eigene Liste pflegen will.
- **Tackles** werden aus Play-by-Play-Zuordnungen (solo/assist je Spieler)
  aggregiert, nicht aus den offiziellen Team-Boxscores - kann punktuell von
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
