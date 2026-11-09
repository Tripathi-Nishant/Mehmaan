import logging
from math import asin, cos, radians, sin, sqrt

logger = logging.getLogger(__name__)

# ponytail: demo cities only; unknown cities skip the distance check (add rows as hosts join).
_CENTRES = {
    ("jaipur", "जयपुर"): (26.9124, 75.7873),
    ("delhi", "new delhi", "दिल्ली", "नई दिल्ली"): (28.6139, 77.2090),
    ("mumbai", "मुंबई"): (19.0760, 72.8777),
    ("varanasi", "banaras", "वाराणसी", "बनारस"): (25.3176, 82.9739),
    ("udaipur", "उदयपुर"): (24.5854, 73.7125),
    ("agra", "आगरा"): (27.1767, 78.0081),
    ("kolkata", "कोलकाता"): (22.5726, 88.3639),
    ("bengaluru", "bangalore", "बेंगलुरु"): (12.9716, 77.5946),
    ("chennai", "चेन्नई"): (13.0827, 80.2707),
    ("hyderabad", "हैदराबाद"): (17.3850, 78.4867),
}
CITY_CENTRES = {name: centre for names, centre in _CENTRES.items() for name in names}

PIN_REJECTIONS = {
    "venue": "Yeh kisi jagah ka naam hai. Kripya ghar par rehkar apni location bhejiye.",
    "forwarded": "Forward ki hui location nahi chalegi. Kripya ghar se nayi location bhejiye.",
    "too_far": "Yeh location aapke shehar se bahut door hai. Kripya ghar se location bhejiye.",
}


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat1, lng1, lat2, lng2 = map(radians, (lat1, lng1, lat2, lng2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


def check_location_pin(
    *, lat: float, lng: float, city: str | None, is_venue: bool, is_forwarded: bool, max_km: float
) -> str | None:
    """Return a rejection reason ("venue", "forwarded", "too_far") or None if the pin is OK."""
    if is_venue:
        return "venue"
    if is_forwarded:
        return "forwarded"
    centre = CITY_CENTRES.get((city or "").strip().lower())
    if centre is None:
        logger.warning("No centre for city %r; skipping pin distance check", city)
        return None
    if distance_km(lat, lng, *centre) > max_km:
        return "too_far"
    return None
