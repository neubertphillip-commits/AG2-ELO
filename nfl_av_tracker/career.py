"""
Career-AV und Weighted Career AV (PFR-Definition):

100% der besten Saison + 95% der zweitbesten + 90% der drittbesten + ...

Fuer "AV je Saison" wird NICHT durch die Anzahl eingerechneter Saisons
geteilt, sondern durch die SUMME der verwendeten Gewichte. Sonst wuerden
laengere Karrieren systematisch bestraft: bei Division durch die reine
Anzahl gehen spaetere Saisons mit sinkendem Gewicht (95%, 90%, ...) voll in
den Nenner ein, aber nur reduziert in den Zaehler - ein Spieler mit 20
gleich guten Saisons haette dann einen niedrigeren Schnitt als einer mit nur
einer einzigen Saison gleicher Qualitaet. Division durch die Gewichtssumme
ist ein echter gewichteter Mittelwert: bei konstanter Saison-AV kommt exakt
diese AV heraus, unabhaengig von der Karrierelaenge.
"""

from __future__ import annotations

import pandas as pd

from .config import AVConfig


def weighted_career_av(cfg: AVConfig, multi_season_av: pd.DataFrame) -> pd.DataFrame:
    if multi_season_av.empty:
        return pd.DataFrame(columns=[
            "player_id", "player_name", "career_av", "weighted_career_av",
            "seasons_played", "seasons_counted", "weighted_av_per_season",
        ])

    # player_id ist der eindeutige Schluessel - NICHT player_name mit
    # einbeziehen: derselbe Spieler kann in verschiedenen Saisons (oder auch
    # innerhalb combine_season_av) mit leicht unterschiedlicher Namens-
    # schreibweise auftauchen, sonst wuerde er in zwei "Karrieren" gesplittet.
    names = multi_season_av.sort_values(
        "player_name", key=lambda s: s.str.len(), ascending=False
    ).groupby("player_id")["player_name"].first()
    per_player_season = multi_season_av.groupby(["player_id", "season"], as_index=False)["av"].sum()

    rows = []
    for pid, g in per_player_season.groupby("player_id"):
        name = names[pid]
        seasons_sorted = g.sort_values("av", ascending=False)["av"].tolist()
        career_av = sum(seasons_sorted)

        weighted_total = 0.0
        weight_sum = 0.0
        seasons_counted = 0
        for i, av in enumerate(seasons_sorted[: cfg.weighted_career_max_seasons]):
            weight = cfg.weighted_career_weight_start - cfg.weighted_career_weight_step * i
            if weight <= 0:
                break
            weighted_total += weight * av
            weight_sum += weight
            seasons_counted += 1

        rows.append({
            "player_id": pid,
            "player_name": name,
            "career_av": career_av,
            "weighted_career_av": weighted_total,
            "seasons_played": len(seasons_sorted),
            "seasons_counted": seasons_counted,
            "weighted_av_per_season": weighted_total / weight_sum if weight_sum else 0.0,
        })

    out = pd.DataFrame(rows)
    return out.sort_values("weighted_career_av", ascending=False).reset_index(drop=True)
