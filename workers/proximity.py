"""
Nearest-worker ranking.

Pure Python, using the existing haversine_distance() from
worker_connect/geolocation.py. Deliberately NOT using that module's
filter_by_distance()/annotate_distance() - those wrap a lazy Django
queryset `.annotate(...)` in a try/except meant to fall back when the DB
lacks trig functions (ACos/Cos/Sin/Radians), but querysets are evaluated
lazily so the except never actually catches anything; the real error would
only surface later when the queryset is iterated. Standard SQLite (used
in local dev here) doesn't have those trig functions built in. Ranking in
Python after the existing category/verified/available filter is simple and
safe at this app's scale (tens-low hundreds of workers per category/city).
"""

from worker_connect.geolocation import haversine_distance


def rank_by_distance(workers, lat, lon, limit=None, include_unlocated=False):
    """
    Sort an iterable of WorkerProfile instances by distance from (lat, lon).

    Returns a plain list, sorted nearest-first, each with a `.distance_km`
    attribute attached for display. Workers with no latitude/longitude
    can't be ranked: they are dropped, or - with include_unlocated, for a
    list a client browses - kept after the located ones, best rated first,
    with distance_km None. Dropping them emptied the client's list whenever
    the client shared a location and the workers had not.
    """
    workers = list(workers)
    located = [w for w in workers if w.latitude is not None and w.longitude is not None]

    for worker in located:
        worker.distance_km = haversine_distance(lat, lon, worker.latitude, worker.longitude)

    located.sort(key=lambda w: w.distance_km)

    if include_unlocated:
        unlocated = [w for w in workers if w.latitude is None or w.longitude is None]
        for worker in unlocated:
            worker.distance_km = None
        unlocated.sort(key=lambda w: -(w.average_rating or 0))
        located += unlocated

    return located[:limit] if limit else located
