"""
Geolocation utilities for Worker Connect.

Provides distance calculations and location-based filtering for jobs and workers.
"""

import math
from typing import Tuple, Optional, List
from django.db.models import QuerySet, F, FloatField, ExpressionWrapper
from django.db.models.functions import ACos, Cos, Sin, Radians


# Earth's radius in kilometers
EARTH_RADIUS_KM = 6371.0
EARTH_RADIUS_MILES = 3959.0


def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    unit: str = 'km'
) -> float:
    """
    Calculate the great circle distance between two points on earth.
    
    Args:
        lat1, lon1: Latitude and longitude of first point
        lat2, lon2: Latitude and longitude of second point
        unit: 'km' for kilometers, 'miles' for miles
        
    Returns:
        Distance in specified unit
    """
    radius = EARTH_RADIUS_KM if unit == 'km' else EARTH_RADIUS_MILES
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    return radius * c


def get_bounding_box(
    lat: float, lon: float,
    distance_km: float
) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box for a given point and distance.
    
    Args:
        lat, lon: Center point coordinates
        distance_km: Distance in kilometers
        
    Returns:
        Tuple of (min_lat, max_lat, min_lon, max_lon)
    """
    # Approximate degrees per km
    lat_delta = distance_km / 111.0
    lon_delta = distance_km / (111.0 * math.cos(math.radians(lat)))
    
    return (
        lat - lat_delta,
        lat + lat_delta,
        lon - lon_delta,
        lon + lon_delta
    )


def filter_by_distance(
    queryset: QuerySet,
    lat: float,
    lon: float,
    max_distance_km: float,
    lat_field: str = 'latitude',
    lon_field: str = 'longitude'
) -> QuerySet:
    """
    Filter queryset by distance from a point.
    
    This uses a two-step approach:
    1. First filter by bounding box (fast, uses indexes)
    2. Then calculate exact distance (accurate)
    
    Args:
        queryset: Django QuerySet to filter
        lat, lon: Center point coordinates
        max_distance_km: Maximum distance in kilometers
        lat_field: Name of latitude field in model
        lon_field: Name of longitude field in model
        
    Returns:
        Filtered QuerySet with distance annotation
    """
    # Step 1: Bounding box filter (fast pre-filter)
    min_lat, max_lat, min_lon, max_lon = get_bounding_box(lat, lon, max_distance_km)
    
    queryset = queryset.filter(
        **{
            f'{lat_field}__gte': min_lat,
            f'{lat_field}__lte': max_lat,
            f'{lon_field}__gte': min_lon,
            f'{lon_field}__lte': max_lon,
        }
    ).exclude(
        **{f'{lat_field}__isnull': True}
    ).exclude(
        **{f'{lon_field}__isnull': True}
    )
    
    # Step 2: Calculate exact distance using Haversine formula in SQL
    # This works with PostgreSQL. For SQLite, we'll use a simpler approximation.
    try:
        queryset = queryset.annotate(
            distance=ExpressionWrapper(
                EARTH_RADIUS_KM * ACos(
                    Cos(Radians(lat)) * Cos(Radians(F(lat_field))) *
                    Cos(Radians(F(lon_field)) - Radians(lon)) +
                    Sin(Radians(lat)) * Sin(Radians(F(lat_field)))
                ),
                output_field=FloatField()
            )
        ).filter(distance__lte=max_distance_km)
    except Exception:
        # Fallback for SQLite: use bounding box only
        pass
    
    return queryset


def annotate_distance(
    queryset: QuerySet,
    lat: float,
    lon: float,
    lat_field: str = 'latitude',
    lon_field: str = 'longitude'
) -> QuerySet:
    """
    Annotate queryset with distance from a point.
    
    Args:
        queryset: Django QuerySet to annotate
        lat, lon: Reference point coordinates
        lat_field: Name of latitude field in model
        lon_field: Name of longitude field in model
        
    Returns:
        QuerySet with 'distance' annotation
    """
    try:
        return queryset.annotate(
            distance=ExpressionWrapper(
                EARTH_RADIUS_KM * ACos(
                    Cos(Radians(lat)) * Cos(Radians(F(lat_field))) *
                    Cos(Radians(F(lon_field)) - Radians(lon)) +
                    Sin(Radians(lat)) * Sin(Radians(F(lat_field)))
                ),
                output_field=FloatField()
            )
        )
    except Exception:
        # Return unmodified queryset if database doesn't support these functions
        return queryset


def parse_coordinates(coord_string: str) -> Optional[Tuple[float, float]]:
    """
    Parse coordinates from string format.
    
    Supports formats:
        - "lat,lon" (e.g., "40.7128,-74.0060")
        - "lat, lon" (with space)
        
    Returns:
        Tuple of (latitude, longitude) or None if invalid
    """
    if not coord_string:
        return None
    
    try:
        parts = coord_string.replace(' ', '').split(',')
        if len(parts) != 2:
            return None
        
        lat = float(parts[0])
        lon = float(parts[1])
        
        # Validate ranges
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None
        
        return (lat, lon)
    except (ValueError, AttributeError):
        return None


def format_distance(distance_km: float, unit: str = 'km') -> str:
    """
    Format distance for display.
    
    Args:
        distance_km: Distance in kilometers
        unit: Output unit ('km' or 'miles')
        
    Returns:
        Formatted string (e.g., "5.2 km" or "3.2 mi")
    """
    if unit == 'miles':
        distance = distance_km * 0.621371
        if distance < 0.1:
            return f"{int(distance * 5280)} ft"
        return f"{distance:.1f} mi"
    else:
        if distance_km < 1:
            return f"{int(distance_km * 1000)} m"
        return f"{distance_km:.1f} km"


# Common location presets (for demo/testing)
DEMO_LOCATIONS = {
    'new_york': (40.7128, -74.0060),
    'los_angeles': (34.0522, -118.2437),
    'chicago': (41.8781, -87.6298),
    'houston': (29.7604, -95.3698),
    'phoenix': (33.4484, -112.0740),
    'london': (51.5074, -0.1278),
    'toronto': (43.6532, -79.3832),
    'sydney': (-33.8688, 151.2093),
}
