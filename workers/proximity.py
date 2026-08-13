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


def rank_by_distance(workers, lat, lon, limit=None):
    """
    Sort an iterable of WorkerProfile instances by distance from (lat, lon).

    Workers with no latitude/longitude are excluded (can't be ranked).
    Returns a plain list, sorted nearest-first, each with a `.distance_km`
    attribute attached for display.
    """
    located = [w for w in workers if w.latitude is not None and w.longitude is not None]

    for worker in located:
        worker.distance_km = haversine_distance(lat, lon, worker.latitude, worker.longitude)

    located.sort(key=lambda w: w.distance_km)

    return located[:limit] if limit else located
