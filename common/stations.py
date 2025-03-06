import random

STATIONS = [
    {
        "id": "workout",
        "frequency": "99.1 FM",
        "name": "PowerMix FM",
        "tagline": "Your ultimate AI-powered workout playlist—never slow down.",
        "description": "Energetic AI-generated beats and dynamic rhythms, designed to fuel high-intensity workouts, fitness routines, and motivation.",
        "instruction": "Generate high-energy, adrenaline-pumping workout music."
    },
    {
        "id": "relaxation",
        "frequency": "88.5 FM",
        "name": "ChillWave Radio",
        "tagline": "Smooth lo-fi vibes to unwind and recharge.",
        "description": "Lo-fi and chill-hop beats crafted by AI for relaxation, sleep aid, and mindfulness moments.",
        "instruction": "Produce calm, soothing tracks perfect for relaxation and mindfulness."
    },
    {
        "id": "deep_focus",
        "frequency": "104.3 FM",
        "name": "Deep Focus Radio",
        "tagline": "Sonic fuel for productivity and deep concentration.",
        "description": "Instrumental, ambient, and minimalistic tunes engineered to help listeners achieve deep productivity and focused workflow.",
        "instruction": "Craft ambient and minimalistic tunes to aid deep concentration and focus."
    },
    {
        "id": "oldies_inspired",
        "frequency": "95.7 FM",
        "name": "Golden Era Hits",
        "tagline": "Modern AI takes on timeless classics.",
        "description": "AI-generated tracks inspired by the melodies and rhythms of Motown, soul, and classic oldies-era music.",
        "instruction": "Create modern twists on classic oldies with soulful, Motown-inspired vibes."
    },
]


def get_random_station():
    """Select and return a random station dictionary."""
    return random.choice(STATIONS)["id"]


def get_station_by_id(station_id):
    """Retrieve a station by its ID."""
    return next((station for station in STATIONS if station["id"] == station_id), None)


def get_station_announcement(station):
    """Format the station announcement in a radio announcer style."""
    tagline = station.get("tagline", "")
    return f"{station['frequency']} {station['name']} - {tagline}"