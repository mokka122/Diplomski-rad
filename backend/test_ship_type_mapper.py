from app.services.ais_ship_type_mapper import (
    map_ais_ship_type,
)


def main():
    print("=" * 80)
    print("OCEANEYE - AIS SHIP TYPE MAPPING TEST")
    print("=" * 80)

    tests = [
        (30, "fishing"),
        (31, "tug"),
        (32, "tug"),
        (52, "tug"),

        (60, "passenger"),
        (65, "passenger"),
        (69, "passenger"),

        (70, "cargo"),
        (75, "cargo"),
        (79, "cargo"),

        (80, "tanker"),
        (85, "tanker"),
        (89, "tanker"),

        (50, "auxiliary"),
        (51, "auxiliary"),
        (54, "auxiliary"),

        (36, None),
        (37, None),
        (90, None),
        (None, None),
        ("invalid", None),
    ]

    all_passed = True

    for ship_type, expected in tests:

        result = map_ais_ship_type(
            ship_type
        )

        passed = (
            result == expected
        )

        all_passed = (
            all_passed
            and passed
        )

        print(
            f"ship_type={str(ship_type):>7} "
            f"-> {str(result):>10} | "
            f"expected={str(expected):>10} | "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()
    print("=" * 80)

    if all_passed:
        print(
            "ALL SHIP TYPE MAPPING TESTS PASSED"
        )
    else:
        print(
            "ONE OR MORE SHIP TYPE MAPPING TESTS FAILED"
        )

    print("=" * 80)


if __name__ == "__main__":
    main()