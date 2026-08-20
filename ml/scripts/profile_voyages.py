from collections import Counter
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
    "imo_nummer",
    "mmsi_nummer",
    "fartoynavn",
    "skipstype",
    "skipsgruppe",
    "flaggkode",
    "avgangshavn_kode",
    "avgangshavn_navn",
    "etd_estimert_avgangstidspunkt",
    "land_avgang",
    "landkode_avgang_totegn",
    "ankomsthavn_kode",
    "ankomsthavn_navn",
    "ankomsttidspunkt",
    "land_ankomst",
    "landkode_ankomst_totegn",
]


def clean_identifier(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def print_counter(title: str, counter: Counter, limit: int = 20) -> None:
    print()
    print(title)
    print("-" * len(title))

    for value, count in counter.most_common(limit):
        print(f"{str(value):40} {count:>10,}")


def profile_year(year: int, file_path: Path) -> dict:
    print()
    print("=" * 100)
    print(f"PROCESSING {year}")
    print("=" * 100)

    total_rows = 0

    unique_vessels = set()
    unique_mmsi = set()
    unique_imo = set()

    departure_ports = Counter()
    arrival_ports = Counter()

    departure_port_names = Counter()
    arrival_port_names = Counter()

    vessel_types = Counter()
    vessel_groups = Counter()

    departure_countries = Counter()
    arrival_countries = Counter()

    monthly_departures = Counter()
    monthly_arrivals = Counter()

    domestic = 0
    international_to_norway = 0
    norway_to_international = 0
    international_other = 0

    reader = pd.read_csv(
        file_path,
        encoding="latin1",
        sep=None,
        engine="python",
        dtype=str,
        usecols=USE_COLUMNS,
        chunksize=CHUNK_SIZE,
    )

    for chunk_number, chunk in enumerate(reader, start=1):
        total_rows += len(chunk)

        print(
            f"{year}: processed "
            f"{total_rows:,} rows"
        )

        for column in [
            "skips_id",
            "mmsi_nummer",
            "imo_nummer",
        ]:
            chunk[column] = clean_identifier(
                chunk[column]
            )

        unique_vessels.update(
            chunk["skips_id"]
            .dropna()
            .unique()
        )

        unique_mmsi.update(
            chunk["mmsi_nummer"]
            .dropna()
            .unique()
        )

        unique_imo.update(
            chunk["imo_nummer"]
            .dropna()
            .unique()
        )

        departure_ports.update(
            chunk["avgangshavn_kode"]
            .dropna()
            .value_counts()
            .to_dict()
        )

        arrival_ports.update(
            chunk["ankomsthavn_kode"]
            .dropna()
            .value_counts()
            .to_dict()
        )

        departure_port_names.update(
            chunk["avgangshavn_navn"]
            .dropna()
            .value_counts()
            .to_dict()
        )

        arrival_port_names.update(
            chunk["ankomsthavn_navn"]
            .dropna()
            .value_counts()
            .to_dict()
        )

        vessel_types.update(
            chunk["skipstype"]
            .dropna()
            .value_counts()
            .to_dict()
        )

        vessel_groups.update(
            chunk["skipsgruppe"]
            .dropna()
            .value_counts()
            .to_dict()
        )

        departure_countries.update(
            chunk["land_avgang"]
            .dropna()
            .value_counts()
            .to_dict()
        )

        arrival_countries.update(
            chunk["land_ankomst"]
            .dropna()
            .value_counts()
            .to_dict()
        )

        departure_time = pd.to_datetime(
            chunk["etd_estimert_avgangstidspunkt"],
            errors="coerce",
            utc=True,
        )

        arrival_time = pd.to_datetime(
            chunk["ankomsttidspunkt"],
            errors="coerce",
            utc=True,
        )

        departure_months = (
            departure_time
            .dt.to_period("M")
            .astype("string")
            .value_counts()
        )

        arrival_months = (
            arrival_time
            .dt.to_period("M")
            .astype("string")
            .value_counts()
        )

        monthly_departures.update(
            departure_months.to_dict()
        )

        monthly_arrivals.update(
            arrival_months.to_dict()
        )

        departure_country = (
            chunk["landkode_avgang_totegn"]
            .astype("string")
            .str.strip()
        )

        arrival_country = (
            chunk["landkode_ankomst_totegn"]
            .astype("string")
            .str.strip()
        )

        is_departure_norway = departure_country.eq("NO")
        is_arrival_norway = arrival_country.eq("NO")

        domestic += (
            is_departure_norway
            & is_arrival_norway
        ).sum()

        international_to_norway += (
            ~is_departure_norway
            & is_arrival_norway
        ).sum()

        norway_to_international += (
            is_departure_norway
            & ~is_arrival_norway
        ).sum()

        international_other += (
            ~is_departure_norway
            & ~is_arrival_norway
        ).sum()

    result = {
        "year": year,
        "total_rows": total_rows,
        "unique_vessels": len(unique_vessels),
        "unique_mmsi": len(unique_mmsi),
        "unique_imo": len(unique_imo),
        "departure_ports": departure_ports,
        "arrival_ports": arrival_ports,
        "departure_port_names": departure_port_names,
        "arrival_port_names": arrival_port_names,
        "vessel_types": vessel_types,
        "vessel_groups": vessel_groups,
        "departure_countries": departure_countries,
        "arrival_countries": arrival_countries,
        "monthly_departures": monthly_departures,
        "monthly_arrivals": monthly_arrivals,
        "domestic": int(domestic),
        "international_to_norway": int(
            international_to_norway
        ),
        "norway_to_international": int(
            norway_to_international
        ),
        "international_other": int(
            international_other
        ),
    }

    return result


def print_year_result(result: dict) -> None:
    year = result["year"]

    print()
    print("=" * 100)
    print(f"RESULTS {year}")
    print("=" * 100)

    print(
        f"Total voyages: "
        f"{result['total_rows']:,}"
    )

    print(
        f"Unique vessel IDs: "
        f"{result['unique_vessels']:,}"
    )

    print(
        f"Unique MMSI: "
        f"{result['unique_mmsi']:,}"
    )

    print(
        f"Unique IMO: "
        f"{result['unique_imo']:,}"
    )

    print()
    print("VOYAGE FLOW")
    print("-" * 40)

    print(
        f"Norway -> Norway: "
        f"{result['domestic']:,}"
    )

    print(
        f"International -> Norway: "
        f"{result['international_to_norway']:,}"
    )

    print(
        f"Norway -> International: "
        f"{result['norway_to_international']:,}"
    )

    print(
        f"Other international: "
        f"{result['international_other']:,}"
    )

    print_counter(
        "TOP 20 DEPARTURE PORTS",
        result["departure_port_names"],
    )

    print_counter(
        "TOP 20 ARRIVAL PORTS",
        result["arrival_port_names"],
    )

    print_counter(
        "TOP 20 VESSEL TYPES",
        result["vessel_types"],
    )

    print_counter(
        "VESSEL GROUPS",
        result["vessel_groups"],
    )

    print_counter(
        "TOP DEPARTURE COUNTRIES",
        result["departure_countries"],
    )

    print_counter(
        "TOP ARRIVAL COUNTRIES",
        result["arrival_countries"],
    )

    print_counter(
        "MONTHLY DEPARTURES",
        result["monthly_departures"],
        limit=24,
    )

    print_counter(
        "MONTHLY ARRIVALS",
        result["monthly_arrivals"],
        limit=24,
    )


def print_combined_summary(results: list[dict]) -> None:
    print()
    print("=" * 100)
    print("COMBINED SUMMARY 2023-2025")
    print("=" * 100)

    total_rows = sum(
        result["total_rows"]
        for result in results
    )

    total_domestic = sum(
        result["domestic"]
        for result in results
    )

    total_international_to_norway = sum(
        result["international_to_norway"]
        for result in results
    )

    total_norway_to_international = sum(
        result["norway_to_international"]
        for result in results
    )

    print(
        f"Total voyages: "
        f"{total_rows:,}"
    )

    print(
        f"Norway -> Norway: "
        f"{total_domestic:,}"
    )

    print(
        f"International -> Norway: "
        f"{total_international_to_norway:,}"
    )

    print(
        f"Norway -> International: "
        f"{total_norway_to_international:,}"
    )

    combined_departure_ports = Counter()
    combined_arrival_ports = Counter()
    combined_vessel_types = Counter()
    combined_vessel_groups = Counter()

    for result in results:
        combined_departure_ports.update(
            result["departure_port_names"]
        )

        combined_arrival_ports.update(
            result["arrival_port_names"]
        )

        combined_vessel_types.update(
            result["vessel_types"]
        )

        combined_vessel_groups.update(
            result["vessel_groups"]
        )

    print_counter(
        "TOP 30 DEPARTURE PORTS - ALL YEARS",
        combined_departure_ports,
        limit=30,
    )

    print_counter(
        "TOP 30 ARRIVAL PORTS - ALL YEARS",
        combined_arrival_ports,
        limit=30,
    )

    print_counter(
        "TOP 30 VESSEL TYPES - ALL YEARS",
        combined_vessel_types,
        limit=30,
    )

    print_counter(
        "VESSEL GROUPS - ALL YEARS",
        combined_vessel_groups,
        limit=20,
    )


def main() -> None:
    print("=" * 100)
    print("OCEANEYE - COMPLETE VOYAGES PROFILING")
    print("=" * 100)

    results = []

    for year, file_path in FILES.items():
        if not file_path.exists():
            print(
                f"ERROR: Missing file: "
                f"{file_path}"
            )
            continue

        result = profile_year(
            year=year,
            file_path=file_path,
        )

        results.append(result)

        print_year_result(result)

    if results:
        print_combined_summary(results)


if __name__ == "__main__":
    main()