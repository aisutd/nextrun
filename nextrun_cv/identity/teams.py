"""Team assignment from torso colour embeddings."""
from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans


def assign_teams(
    track_emb: dict[int, np.ndarray],
    n_teams: int = 2,
    seeds: dict[str, list[np.ndarray]] | None = None,
) -> dict[int, str]:
    """track_id -> team label.

    seeds: {team_name: [embeddings of tagged players on that team]}. When the user tagged at least
    one player per team, untagged tracks go to the nearest team centroid; otherwise k-means and
    teams are named "A", "B", ..."""
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
    km = KMeans(n_clusters=n_teams, n_init=10, random_state=0).fit(X)
    letters = "ABCDEFGH"
    # deterministic naming: biggest cluster is "A"
    order = np.argsort(-np.bincount(km.labels_, minlength=n_teams))
    rename = {int(c): letters[i] for i, c in enumerate(order)}
    return {t: rename[int(l)] for t, l in zip(tids, km.labels_)}
