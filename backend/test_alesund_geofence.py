from app.services.alesund_geofence import (
    get_alesund_geofence,
    is_inside_alesund,
)


def main() -> None:
    print("=" * 80)
    print("OCEANEYE - ÅLESUND GEOFENCE TEST")
    print("=" * 80)

    geofence = get_alesund_geofence()

    print()
    print("Configured geofence:")
    print(geofence)

    tests = [
        {
            "name": "Central Ålesund",
            "latitude": 62.4722,
            "longitude": 6.1495,
            "expected": True,
        },
        {
            "name": "Near Ålesund harbour",
            "latitude": 62.4680,
            "longitude": 6.1300,
            "expected": True,
        },
        {
            "name": "Far south",
            "latitude": 62.20,
            "longitude": 6.15,
            "expected": False,
        },
        {
            "name": "Far east",
            "latitude": 62.47,
            "longitude": 7.00,
            "expected": False,
        },
    ]

    print()
    print("Tests:")
    print("-" * 80)

    all_passed = True

    for test in tests:
        result = is_inside_alesund(
            latitude=test["latitude"],
            longitude=test["longitude"],
        )

        passed = (
            result
            ==
            test["expected"]
        )

        all_passed = (
            all_passed
            and passed
        )

        print(
            f"{test['name']}: "
            f"inside={result} | "
            f"expected={test['expected']} | "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()
    print("=" * 80)

    if all_passed:
        print("ALL GEOFENCE TESTS PASSED")
    else:
        print("ONE OR MORE TESTS FAILED")

    print("=" * 80)


if __name__ == "__main__":
    main()