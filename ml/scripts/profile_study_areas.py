from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

FILES = {
    2023: RAW_DIR / "voyages_2023.csv",
    2024: RAW_DIR / "voyages_2024.csv",
    2025: RAW_DIR / "voyages_2025.csv",
}

CHUNK_SIZE = 100_000

USE_COLUMNS = [
    "seilas_id",
    "skips_id",
    "mmsi_nummer",
    "skipstype",
    "skipsgruppe",
    "etd_estimert_avgangstidspunkt",
    "ankomsttidspunkt",
    "landkode_avgang_totegn",
    "landkode_ankomst_totegn",
    "fylkesnavn_avgang",
    "fylkesnavn_ankomst",
    "kommunenavn_avgang",
    "kommunenavn_ankomst",
    "avgangshavn_navn",
    "ankomsthavn_navn",
]


def normalize_text(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
    )


def update_counter(counter: Counter, series: pd.Series) -> None:
    counter.update(
        series
        .dropna()
        .value_counts()
        .to_dict()
    )


def profile_year(year: int, path: Path) -> dict:
    print()
    print("=" * 100)
    print(f"PROCESSING STUDY AREAS - {year}")
    print("=" * 100)

    municipality_departures = Counter()
    municipality_arrivals = Counter()

    county_departures = Counter()
    county_arrivals = Counter()

    municipality_activity = Counter()

    monthly_by_municipality = defaultdict(Counter)

    municipality_vessels = defaultdict(set)

    total_rows = 0

    reader = pd.read_csv(
        path,
        encoding="latin1",
        sep=None,
        engine="python",
        dtype=str,
        usecols=USE_COLUMNS,
        chunksize=CHUNK_SIZE,
    )

    for chunk in reader:
        total_rows += len(chunk)

        print(
            f"{year}: processed {total_rows:,} rows"
        )

        text_columns = [
            "kommunenavn_avgang",
            "kommunenavn_ankomst",
            "fylkesnavn_avgang",
            "fylkesnavn_ankomst",
            "landkode_avgang_totegn",
            "landkode_ankomst_totegn",
        ]

        for column in text_columns:
            chunk[column] = normalize_text(
                chunk[column]
            )

        #
        # Only Norwegian municipality observations
        #
        departure_no = (
            chunk["landkode_avgang_totegn"] == "NO"
        )

        arrival_no = (
            chunk["landkode_ankomst_totegn"] == "NO"
        )

        norwegian_departures = chunk.loc[
            departure_no
        ]

        norwegian_arrivals = chunk.loc[
            arrival_no
        ]

        update_counter(
            municipality_departures,
            norwegian_departures[
                "kommunenavn_avgang"
            ],
        )

        update_counter(
            municipality_arrivals,
            norwegian_arrivals[
                "kommunenavn_ankomst"
            ],
        )

        update_counter(
            county_departures,
            norwegian_departures[
                "fylkesnavn_avgang"
            ],
        )

        update_counter(
            county_arrivals,
            norwegian_arrivals[
                "fylkesnavn_ankomst"
            ],
        )

        #
        # Total municipality activity:
        # arrival + departure
        #
        departure_counts = (
            norwegian_departures[
                "kommunenavn_avgang"
            ]
            .dropna()
            .value_counts()
        )

        arrival_counts = (
            norwegian_arrivals[
                "kommunenavn_ankomst"
            ]
            .dropna()
            .value_counts()
        )

        municipality_activity.update(
            departure_counts.to_dict()
        )

        municipality_activity.update(
            arrival_counts.to_dict()
        )

        #
        # Unique vessels by municipality
        #
        for municipality, group in (
            norwegian_departures
            .dropna(
                subset=[
                    "kommunenavn_avgang"
                ]
            )
            .groupby(
                "kommunenavn_avgang"
            )
        ):
            vessels = (
                group["mmsi_nummer"]
                .dropna()
                .astype(str)
                .str.replace(
                    r"\.0$",
                    "",
                    regex=True,
                )
                .unique()
            )

            municipality_vessels[
                municipality
            ].update(vessels)

        for municipality, group in (
            norwegian_arrivals
            .dropna(
                subset=[
                    "kommunenavn_ankomst"
                ]
            )
            .groupby(
                "kommunenavn_ankomst"
            )
        ):
            vessels = (
                group["mmsi_nummer"]
                .dropna()
                .astype(str)
                .str.replace(
                    r"\.0$",
                    "",
                    regex=True,
                )
                .unique()
            )

            municipality_vessels[
                municipality
            ].update(vessels)

        #
        # Monthly activity by municipality
        #
        departure_times = pd.to_datetime(
            norwegian_departures[
                "etd_estimert_avgangstidspunkt"
            ],
            errors="coerce",
            utc=True,
        )

        arrival_times = pd.to_datetime(
            norwegian_arrivals[
                "ankomsttidspunkt"
            ],
            errors="coerce",
            utc=True,
        )

        dep_temp = pd.DataFrame(
            {
                "municipality":
                    norwegian_departures[
                        "kommunenavn_avgang"
                    ],
                "time": departure_times,
            }
        )

        arr_temp = pd.DataFrame(
            {
                "municipality":
                    norwegian_arrivals[
                        "kommunenavn_ankomst"
                    ],
                "time": arrival_times,
            }
        )

        dep_temp = dep_temp.dropna()

        arr_temp = arr_temp.dropna()

        dep_temp["month"] = (
            dep_temp["time"]
            .dt.strftime("%Y-%m")
        )

        arr_temp["month"] = (
            arr_temp["time"]
            .dt.strftime("%Y-%m")
        )

        dep_month_counts = (
            dep_temp
            .groupby(
                [
                    "municipality",
                    "month",
                ]
            )
            .size()
        )

        arr_month_counts = (
            arr_temp
            .groupby(
                [
                    "municipality",
                    "month",
                ]
            )
            .size()
        )

        for (
            municipality,
            month,
        ), count in dep_month_counts.items():

            monthly_by_municipality[
                municipality
            ][month] += int(count)

        for (
            municipality,
            month,
        ), count in arr_month_counts.items():

            monthly_by_municipality[
                municipality
            ][month] += int(count)

    return {
        "year": year,
        "total_rows": total_rows,
        "departures": municipality_departures,
        "arrivals": municipality_arrivals,
        "activity": municipality_activity,
        "county_departures": county_departures,
        "county_arrivals": county_arrivals,
        "vessels": municipality_vessels,
        "monthly": monthly_by_municipality,
    }


def print_top_municipalities(result: dict) -> None:
    print()
    print("=" * 100)
    print(
        f"TOP MUNICIPALITIES - {result['year']}"
    )
    print("=" * 100)

    print(
        f"{'Municipality':30}"
        f"{'Activity':>12}"
        f"{'Unique MMSI':>15}"
    )

    print("-" * 60)

    for municipality, count in (
        result["activity"]
        .most_common(30)
    ):
        unique_vessels = len(
            result["vessels"].get(
                municipality,
                set(),
            )
        )

        print(
            f"{municipality:30}"
            f"{count:>12,}"
            f"{unique_vessels:>15,}"
        )


def print_combined(results: list[dict]) -> None:
    combined_activity = Counter()

    combined_vessels = defaultdict(set)

    combined_monthly = defaultdict(Counter)

    for result in results:
        combined_activity.update(
            result["activity"]
        )

        for municipality, vessels in (
            result["vessels"].items()
        ):
            combined_vessels[
                municipality
            ].update(vessels)

        for municipality, months in (
            result["monthly"].items()
        ):
            combined_monthly[
                municipality
            ].update(months)

    print()
    print("=" * 100)
    print("COMBINED MUNICIPALITY RANKING 2023-2025")
    print("=" * 100)

    print(
        f"{'Municipality':30}"
        f"{'Activity':>12}"
        f"{'Unique MMSI':>15}"
    )

    print("-" * 60)

    for municipality, count in (
        combined_activity.most_common(40)
    ):

        print(
            f"{municipality:30}"
            f"{count:>12,}"
            f"{len(combined_vessels[municipality]):>15,}"
        )

    #
    # Detailed candidates
    #
    candidate_names = [
        "Ålesund",
        "Oslo",
        "Bergen",
        "Tromsø",
        "Stavanger",
        "Molde",
        "Kristiansund",
    ]

    for municipality in candidate_names:

        if municipality not in combined_activity:
            continue

        print()
        print("=" * 100)
        print(
            f"CANDIDATE: {municipality}"
        )
        print("=" * 100)

        print(
            f"Total arrival + departure events: "
            f"{combined_activity[municipality]:,}"
        )

        print(
            f"Unique MMSI: "
            f"{len(combined_vessels[municipality]):,}"
        )

        print()
        print("MONTHLY ACTIVITY")
        print("-" * 40)

        months = combined_monthly[
            municipality
        ]

        for month in sorted(months):
            print(
                f"{month}: "
                f"{months[month]:,}"
            )


def main() -> None:
    print("=" * 100)
    print("OCEANEYE - STUDY AREA PROFILING")
    print("=" * 100)

    results = []

    for year, path in FILES.items():

        result = profile_year(
            year=year,
            path=path,
        )

        results.append(result)

        print_top_municipalities(
            result
        )

    print_combined(results)


if __name__ == "__main__":
    main()