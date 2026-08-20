from typing import Optional


# ======================================================================================
# OCEANEYE LIVE VESSEL GROUPS
# ======================================================================================
#
# Historical SafeSeaNet data uses:
#
#     Passasjer
#     Last
#     Fisk
#     Tank
#     Auxiliary
#     Slep
#
# Live BarentsWatch AIS uses numeric AIS ship type codes.
#
# These classifications are NOT identical.
#
# This module therefore provides a deliberate operational proxy mapping so that
# live AIS events can be aggregated into approximately compatible feature groups.
#
# The mapping is intentionally simple and documented.
# ======================================================================================


GROUP_PASSENGER = "passenger"
GROUP_CARGO = "cargo"
GROUP_FISHING = "fishing"
GROUP_TANKER = "tanker"
GROUP_AUXILIARY = "auxiliary"
GROUP_TUG = "tug"


SUPPORTED_GROUPS = [
    GROUP_PASSENGER,
    GROUP_CARGO,
    GROUP_FISHING,
    GROUP_TANKER,
    GROUP_AUXILIARY,
    GROUP_TUG,
]


# ======================================================================================
# SPECIAL AIS TYPES
# ======================================================================================

# Fishing vessel
FISHING_TYPES = {
    30,
}


# Towing / tug-related AIS vessel types.
#
# 31 = towing
# 32 = towing with large tow
# 52 = tug
TUG_TYPES = {
    31,
    32,
    52,
}


# Auxiliary/service-oriented types.
#
# This is an OceanEye operational proxy for the historical
# SafeSeaNet "Auxiliary" group.
#
# It deliberately excludes sailing / pleasure craft because
# those do not represent the same operational category.
AUXILIARY_TYPES = {
    33,  # dredging / underwater operations
    34,  # diving operations
    35,  # military operations

    50,  # pilot vessel
    51,  # search and rescue
    53,  # port tender
    54,  # anti-pollution equipment
    55,  # law enforcement
    58,  # medical transport
    59,  # noncombatant ship
}


def normalize_ship_type(
    ship_type,
) -> Optional[int]:
    """
    Safely normalize an AIS ship type into an integer.

    Returns None for missing or invalid values.
    """

    if ship_type is None:
        return None

    try:
        value = int(
            ship_type
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    if value < 0 or value > 99:
        return None

    return value


def map_ais_ship_type(
    ship_type,
) -> Optional[str]:
    """
    Map numeric AIS ship type into one of the six OceanEye
    live traffic groups.

    Returns:
        passenger
        cargo
        fishing
        tanker
        auxiliary
        tug

    Unknown / unsupported AIS types return None.
    """

    value = normalize_ship_type(
        ship_type
    )

    if value is None:
        return None

    # Fishing
    if value in FISHING_TYPES:
        return GROUP_FISHING

    # Towing / tug
    if value in TUG_TYPES:
        return GROUP_TUG

    # Passenger ships
    if 60 <= value <= 69:
        return GROUP_PASSENGER

    # Cargo ships
    if 70 <= value <= 79:
        return GROUP_CARGO

    # Tankers
    if 80 <= value <= 89:
        return GROUP_TANKER

    # Service / auxiliary proxy
    if value in AUXILIARY_TYPES:
        return GROUP_AUXILIARY

    return None


def get_ship_type_mapping_info() -> dict:
    """
    Return mapping documentation for API/debugging.
    """

    return {
        "mapping_type": (
            "OceanEye proxy mapping from AIS ship type "
            "to SafeSeaNet-compatible traffic groups"
        ),

        "groups": {
            "passenger": "AIS 60-69",
            "cargo": "AIS 70-79",
            "fishing": "AIS 30",
            "tanker": "AIS 80-89",
            "tug": "AIS 31, 32, 52",
            "auxiliary": (
                "AIS 33, 34, 35, 50, 51, "
                "53, 54, 55, 58, 59"
            ),
        },

        "important_note": (
            "AIS ship type and SafeSeaNet skipsgruppe are different "
            "classification systems. This mapping is an operational "
            "proxy used for live OceanEye feature generation."
        ),
    }