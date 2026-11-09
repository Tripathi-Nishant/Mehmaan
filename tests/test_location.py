from app.host_bot.location import check_location_pin, distance_km

HAWA_MAHAL = (26.9239, 75.8267)
INDIA_GATE = (28.6129, 77.2295)


def check(lat_lng=HAWA_MAHAL, city="Jaipur", venue=False, forwarded=False):
    lat, lng = lat_lng
    return check_location_pin(
        lat=lat, lng=lng, city=city, is_venue=venue, is_forwarded=forwarded, max_km=50
    )


def test_valid_pin_near_city_is_accepted():
    assert check() is None


def test_venue_is_rejected():
    assert check(venue=True) == "venue"


def test_forwarded_pin_is_rejected():
    assert check(forwarded=True) == "forwarded"


def test_pin_far_from_city_is_rejected():
    assert check(lat_lng=INDIA_GATE, city="Jaipur") == "too_far"


def test_city_match_ignores_case_and_accepts_hindi():
    assert check(city="jaipur") is None
    assert check(city="जयपुर") is None
    assert check(lat_lng=INDIA_GATE, city="जयपुर") == "too_far"


def test_unknown_city_skips_distance_check():
    assert check(lat_lng=INDIA_GATE, city="Bundi") is None


def test_distance_jaipur_to_delhi_is_about_240_km():
    assert 230 < distance_km(*HAWA_MAHAL, *INDIA_GATE) < 250
