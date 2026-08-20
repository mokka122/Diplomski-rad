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


def count_rows(file_path: Path) -> int:
    with open(
        file_path,
        "r",
        encoding="latin1",
        errors="ignore",
    ) as file:
        return sum(1 for _ in file) - 1


def inspect_file(year: int, file_path: Path) -> None:
    print()
    print("=" * 100)
    print(f"VOYAGES {year}")
    print("=" * 100)

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return

    print(f"File: {file_path}")
    print(f"Size: {file_path.stat().st_size / (1024 ** 2):.2f} MB")

    row_count = count_rows(file_path)

    print(f"Rows: {row_count:,}")

    sample = pd.read_csv(
        file_path,
        encoding="latin1",
        sep=None,
        engine="python",
        nrows=10_000,
        dtype=str,
    )

    print(f"Columns: {len(sample.columns)}")

    print("\nCOLUMN NAMES:")
    for index, column in enumerate(sample.columns):
        print(f"{index:02d}: {column}")

    print("\nFIRST 3 ROWS:")
    print(
        sample.head(3).to_string(
            index=False
        )
    )

    print("\nMISSING VALUES - SAMPLE OF 10,000:")
    missing = (
        sample.isna()
        .sum()
        .sort_values(ascending=False)
    )

    print(missing.to_string())

    print("\nMISSING PERCENTAGE - SAMPLE OF 10,000:")
    missing_percentage = (
        sample.isna()
        .mean()
        .mul(100)
        .sort_values(ascending=False)
    )

    print(
        missing_percentage
        .round(2)
        .to_string()
    )

    print("\nUNIQUE VALUES - SAMPLE OF 10,000:")
    unique = (
        sample.nunique(
            dropna=True
        )
        .sort_values(ascending=False)
    )

    print(unique.to_string())

    print("\nKEY FIELD STATISTICS:")

    key_fields = [
        "seilas_id",
        "skips_id",
        "imo_nummer",
        "mmsi_nummer",
        "skipstype",
        "skipsgruppe",
        "avgangshavn_kode",
        "ankomsthavn_kode",
        "land_avgang",
        "land_ankomst",
    ]

    for field in key_fields:
        if field not in sample.columns:
            continue

        print(
            f"{field}: "
            f"{sample[field].nunique(dropna=True):,} "
            f"unique values"
        )


def main() -> None:
    print("=" * 100)
    print("OCEANEYE - VOYAGES DATASET INSPECTION")
    print("=" * 100)

    for year, file_path in FILES.items():
        inspect_file(
            year=year,
            file_path=file_path,
        )


if __name__ == "__main__":
    main()