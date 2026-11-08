from collections.abc import Mapping


def format_rupees(paise: int) -> str:
    return f"₹{paise // 100:,}"


def render_readback(fields: Mapping[str, object], commission_bps: int = 1500) -> str:
    price = int(fields["price_per_person_paise"])
    payout = price * (10_000 - commission_bps) // 10_000
    return (
        f"Aap {fields['activity_description']} karengi. "
        f"Yeh {fields['duration_min']} minute ka anubhav hai, zyada se zyada "
        f"{fields['max_guests']} mehmaan. "
        f"Shehar {fields['city']}, ilaaka {fields['area']}. "
        f"Shuruat {fields['start_time_local']} baje. "
        f"Daam {format_rupees(price)} prati vyakti. "
        f"Guest {format_rupees(price)} dega, aapko {format_rupees(payout)} milenge. "
        f"Landmark {fields['landmark']}. Cancellation niyam: {fields['cancellation_rule']}. "
        f"Location shared hai, aur voice clip consent "
        f"{'haan' if fields['consent_voice_clip'] else 'nahi'}. "
        "Kya yeh sahi hai? Haan ya badalna hai?"
    )
