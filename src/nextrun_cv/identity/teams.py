"""Team assignment from torso colour embeddings."""
from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans


def assign_teams(
    track_emb: dict[int, np.ndarray],
    n_teams: int = 2,
    seeds: dict[str, list[np.ndarray]] | None = None,
    weights: dict[int, float] | None = None,
    max_other_share: float = 0.0,
) -> dict[int, str]:
    """track_id -> team label.

    seeds: {team_name: [embeddings of tagged players on that team]}. When the user tagged at least
    one player per team, untagged tracks go to the nearest team centroid; otherwise k-means and
    teams are named "A", "B", ...
    max_other_share > 0: also try one extra cluster (referees, people at the court edge); when it holds at most
    this share of the weight (track frames), its tracks get no team instead of being forced into one."""
    if not track_emb:
        return {}
    tids = list(track_emb)
    X = np.stack([track_emb[t] for t in tids])
    if seeds and len(seeds) >= 2:
        names = list(seeds)
        C = np.stack([np.mean(seeds[n], axis=0) for n in names])
        lab = np.argmax(X @ C.T, axis=1)
        return {t: names[l] for t, l in zip(tids, lab)}
    if len(tids) < n_teams:
        return {t: "A" for t in tids}
    w = np.array([(weights or {}).get(t, 1.0) for t in tids], float)
    letters = "ABCDEFGH"
    if max_other_share > 0 and len(tids) > n_teams + 1:
        km = KMeans(n_clusters=n_teams + 1, n_init=10, random_state=0).fit(X, sample_weight=w)
        share = np.bincount(km.labels_, weights=w, minlength=n_teams + 1) / w.sum()
        other = int(np.argmin(share))
        if share[other] <= max_other_share:
            order = [int(c) for c in np.argsort(-share) if c != other]
            rename = {c: letters[i] for i, c in enumerate(order)}
            return {t: rename[int(l)] for t, l in zip(tids, km.labels_) if int(l) != other}
    km = KMeans(n_clusters=n_teams, n_init=10, random_state=0).fit(X, sample_weight=w)
    # deterministic naming: biggest cluster is "A"
    order = np.argsort(-np.bincount(km.labels_, weights=w, minlength=n_teams))
    rename = {int(c): letters[i] for i, c in enumerate(order)}
    return {t: rename[int(l)] for t, l in zip(tids, km.labels_)}
