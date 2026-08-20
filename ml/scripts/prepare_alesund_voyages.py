from pathlib import Path

import pandas as pd


# ==================================================================================================
# PATHS / CONFIGURATION
# ==================================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

FILES = {
    2023: RAW_DIR / "voyages_2023.csv",
    2024: RAW_DIR / "voyages_2024.csv",
    2025: RAW_DIR / "voyages_2025.csv",
}

CHUNK_SIZE = 100_000

STUDY_AREA = "Ålesund"


# ==================================================================================================
# COLUMNS
# ==================================================================================================

KEEP_COLUMNS = [
    "seilas_id",
    "skips_id",
    "imo_nummer",
    "mmsi_nummer",
    "kallesignal",
    "fartoynavn",

    "byggeaar",
    "bruttotonnasje_bt",
    "doedvekttonn_dwt",
    "lengde",
    "bredde",
    "dypgaaende",

    "skipstype",
    "skipsgruppe",

    "flaggkode",
    "flaggstat",
    "farlig_last_hazmat",

    "avgangshavn_id",
    "avgangshavn_kode",
    "avgangshavn_navn",
    "etd_estimert_avgangstidspunkt",
    "land_avgang",
    "landkode_avgang_totegn",
    "fylkesnavn_avgang",
    "kommunenavn_avgang",

    "ankomsthavn_id",
    "ankomsthavn_kode",
    "ankomsthavn_navn",
    "ankomsttidspunkt",
    "land_ankomst",
    "landkode_ankomst_totegn",
    "fylkesnavn_ankomst",
    "kommunenavn_ankomst",
]


IDENTIFIER_COLUMNS = [
    "seilas_id",
    "skips_id",
    "imo_nummer",
    "mmsi_nummer",
    "avgangshavn_id",
    "ankomsthavn_id",
]


NUMERIC_COLUMNS = [
    "byggeaar",
    "bruttotonnasje_bt",
    "doedvekttonn_dwt",
    "lengde",
    "bredde",
    "dypgaaende",
]


TEXT_COLUMNS = [
    "kallesignal",
    "fartoynavn",
    "skipstype",
    "skipsgruppe",
    "flaggkode",
    "flaggstat",
    "farlig_last_hazmat",

    "avgangshavn_kode",
    "avgangshavn_navn",
    "land_avgang",
    "landkode_avgang_totegn",
    "fylkesnavn_avgang",
    "kommunenavn_avgang",

    "ankomsthavn_kode",
    "ankomsthavn_navn",
    "land_ankomst",
    "landkode_ankomst_totegn",
    "fylkesnavn_ankomst",
    "kommunenavn_ankomst",
]


# ==================================================================================================
# NORMALIZATION HELPERS
# ==================================================================================================

def normalize_identifier(series: pd.Series) -> pd.Series:
    """
    Normalize identifier columns.

    Examples:
        259222000.0  -> 259222000
        259222000,0  -> 259222000

    IDs remain strings because MMSI / IMO / internal IDs
    are identifiers, not numerical measurements.
    """

    cleaned = (
        series
        .astype("string")
        .str.strip()
        .str.replace(
            r"[,.]0$",
            "",
            regex=True,
        )
    )

    cleaned = cleaned.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "<NA>": pd.NA,
            "None": pd.NA,
        }
    )

    return cleaned


def normalize_numeric(series: pd.Series) -> pd.Series:
    """
    Convert Norwegian decimal comma values to proper numeric values.

    Example:
        '223,899993896484'
            ->
        223.899993896484
    """

    cleaned = (
        series
        .astype("string")
        .str.strip()
        .str.replace(
            ",",
            ".",
            regex=False,
        )
    )

    return pd.to_numeric(
        cleaned,
        errors="coerce",
    )


def normalize_text(series: pd.Series) -> pd.Series:
    """
    Normalize text while preserving missing values.
    """

    cleaned = (
        series
        .astype("string")
        .str.strip()
    )

    cleaned = cleaned.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "<NA>": pd.NA,
            "None": pd.NA,
        }
    )

    return cleaned


# ==================================================================================================
# CLEANING
# ==================================================================================================

def clean_chunk(
    chunk: pd.DataFrame,
    year: int,
) -> pd.DataFrame:

    # ----------------------------------------------------------------------------------------------
    # Normalize text columns
    # ----------------------------------------------------------------------------------------------

    for column in TEXT_COLUMNS:
        if column in chunk.columns:
            chunk[column] = normalize_text(
                chunk[column]
            )

    # ----------------------------------------------------------------------------------------------
    # Study-area filter
    #
    # Voyage is relevant when:
    #
    # departure municipality = Ålesund
    # OR
    # arrival municipality = Ålesund
    #
    # and the respective country is Norway.
    # ----------------------------------------------------------------------------------------------

    departure_in_alesund = (
        chunk["kommunenavn_avgang"]
        .eq(STUDY_AREA)
        &
        chunk["landkode_avgang_totegn"]
        .eq("NO")
    )

    arrival_in_alesund = (
        chunk["kommunenavn_ankomst"]
        .eq(STUDY_AREA)
        &
        chunk["landkode_ankomst_totegn"]
        .eq("NO")
    )

    # IMPORTANT:
    # Pandas StringDtype comparisons may return pd.NA.
    # Those must explicitly become False before boolean operations.

    departure_in_alesund = (
        departure_in_alesund
        .fillna(False)
        .astype(bool)
    )

    arrival_in_alesund = (
        arrival_in_alesund
        .fillna(False)
        .astype(bool)
    )

    study_area_mask = (
        departure_in_alesund
        | arrival_in_alesund
    )

    chunk = chunk.loc[
        study_area_mask
    ].copy()

    if chunk.empty:
        return chunk

    # Save the study-area flags AFTER filtering,
    # preserving the indexes of the retained rows.

    chunk["departure_in_study_area"] = (
        departure_in_alesund
        .loc[chunk.index]
        .fillna(False)
        .astype(bool)
    )

    chunk["arrival_in_study_area"] = (
        arrival_in_alesund
        .loc[chunk.index]
        .fillna(False)
        .astype(bool)
    )

    # ----------------------------------------------------------------------------------------------
    # Normalize identifiers
    # ----------------------------------------------------------------------------------------------

    for column in IDENTIFIER_COLUMNS:
        if column in chunk.columns:
            chunk[column] = normalize_identifier(
                chunk[column]
            )

    # ----------------------------------------------------------------------------------------------
    # Normalize numeric vessel attributes
    # ----------------------------------------------------------------------------------------------

    for column in NUMERIC_COLUMNS:
        if column in chunk.columns:
            chunk[column] = normalize_numeric(
                chunk[column]
            )

    # ----------------------------------------------------------------------------------------------
    # Timestamps
    #
    # Original data includes offsets such as:
    #
    # 2025-06-20 18:00:00+02:00
    #
    # We normalize all timestamps to UTC.
    # ----------------------------------------------------------------------------------------------

    chunk["departure_time"] = pd.to_datetime(
        chunk[
            "etd_estimert_avgangstidspunkt"
        ],
        errors="coerce",
        utc=True,
    )

    chunk["arrival_time"] = pd.to_datetime(
        chunk[
            "ankomsttidspunkt"
        ],
        errors="coerce",
        utc=True,
    )

    # ----------------------------------------------------------------------------------------------
    # Dataset metadata
    # ----------------------------------------------------------------------------------------------

    chunk["source_year"] = year

    # 2023 is kept for exploratory/reference purposes,
    # while 2024-2025 are considered the primary ML period.

    chunk["primary_ml_period"] = (
        year >= 2024
    )

    # ----------------------------------------------------------------------------------------------
    # MMSI validation
    #
    # Standard MMSI should contain exactly 9 digits.
    #
    # We do NOT delete the whole voyage if MMSI is malformed.
    # Instead, the invalid MMSI is set to missing.
    # ----------------------------------------------------------------------------------------------

    if "mmsi_nummer" in chunk.columns:

        valid_mmsi = (
            chunk["mmsi_nummer"]
            .str.fullmatch(
                r"\d{9}",
                na=False,
            )
        )

        invalid_mmsi = (
            chunk["mmsi_nummer"]
            .notna()
            &
            ~valid_mmsi
        )

        chunk.loc[
            invalid_mmsi,
            "mmsi_nummer"
        ] = pd.NA

    # ----------------------------------------------------------------------------------------------
    # IMO validation
    #
    # IMO numbers normally contain 7 digits.
    #
    # We only perform format validation here.
    # We are not yet implementing the IMO checksum.
    # ----------------------------------------------------------------------------------------------

    if "imo_nummer" in chunk.columns:

        valid_imo = (
            chunk["imo_nummer"]
            .str.fullmatch(
                r"\d{7}",
                na=False,
            )
        )

        invalid_imo = (
            chunk["imo_nummer"]
            .notna()
            &
            ~valid_imo
        )

        chunk.loc[
            invalid_imo,
            "imo_nummer"
        ] = pd.NA

    # ----------------------------------------------------------------------------------------------
    # Basic physical validation
    # ----------------------------------------------------------------------------------------------

    if "lengde" in chunk.columns:

        invalid_length = (
            chunk["lengde"].notna()
            &
            (
                (chunk["lengde"] <= 0)
                |
                (chunk["lengde"] > 500)
            )
        )

        chunk.loc[
            invalid_length,
            "lengde"
        ] = pd.NA

    if "bredde" in chunk.columns:

        invalid_width = (
            chunk["bredde"].notna()
            &
            (
                (chunk["bredde"] <= 0)
                |
                (chunk["bredde"] > 100)
            )
        )

        chunk.loc[
            invalid_width,
            "bredde"
        ] = pd.NA

    if "dypgaaende" in chunk.columns:

        invalid_draft = (
            chunk["dypgaaende"].notna()
            &
            (
                (chunk["dypgaaende"] < 0)
                |
                (chunk["dypgaaende"] > 30)
            )
        )

        chunk.loc[
            invalid_draft,
            "dypgaaende"
        ] = pd.NA

    if "byggeaar" in chunk.columns:

        invalid_build_year = (
            chunk["byggeaar"].notna()
            &
            (
                (chunk["byggeaar"] < 1800)
                |
                (chunk["byggeaar"] > year)
            )
        )

        chunk.loc[
            invalid_build_year,
            "byggeaar"
        ] = pd.NA

    # ----------------------------------------------------------------------------------------------
    # Optional useful derived field:
    # voyage duration in hours
    #
    # IMPORTANT:
    # departure timestamp is ETD (estimated departure),
    # so this value must be interpreted carefully.
    # ----------------------------------------------------------------------------------------------

    chunk["voyage_duration_hours"] = (
        (
            chunk["arrival_time"]
            -
            chunk["departure_time"]
        )
        .dt.total_seconds()
        / 3600
    )

    # Negative duration cannot represent a valid chronological voyage.
    # We do not delete the record; only mark the duration unavailable.

    chunk.loc[
        chunk["voyage_duration_hours"] < 0,
        "voyage_duration_hours"
    ] = pd.NA

    return chunk


# ==================================================================================================
# YEAR PROCESSING
# ==================================================================================================

def process_year(
    year: int,
    file_path: Path,
) -> pd.DataFrame:

    print()
    print("=" * 100)
    print(f"PROCESSING {year}")
    print("=" * 100)

    processed_chunks = []

    total_read = 0
    total_kept = 0

    reader = pd.read_csv(
        file_path,
        encoding="latin1",
        sep=None,
        engine="python",
        dtype=str,
        usecols=KEEP_COLUMNS,
        chunksize=CHUNK_SIZE,
    )

    for chunk_number, chunk in enumerate(
        reader,
        start=1,
    ):

        total_read += len(chunk)

        cleaned = clean_chunk(
            chunk=chunk,
            year=year,
        )

        total_kept += len(cleaned)

        if not cleaned.empty:
            processed_chunks.append(
                cleaned
            )

        print(
            f"{year}: "
            f"chunk={chunk_number} | "
            f"read={total_read:,} | "
            f"Ålesund={total_kept:,}"
        )

    if not processed_chunks:

        print(
            f"WARNING: No Ålesund records "
            f"found for {year}."
        )

        return pd.DataFrame()

    result = pd.concat(
        processed_chunks,
        ignore_index=True,
    )

    # ----------------------------------------------------------------------------------------------
    # Duplicate voyage IDs
    #
    # According to the profiling, seilas_id behaves as a voyage-level identifier.
    # We therefore keep one record per seilas_id.
    # ----------------------------------------------------------------------------------------------

    before_duplicates = len(result)

    result = (
        result
        .drop_duplicates(
            subset=["seilas_id"],
            keep="first",
        )
        .reset_index(drop=True)
    )

    removed_duplicates = (
        before_duplicates
        -
        len(result)
    )

    print()
    print(
        f"{year}: duplicates removed: "
        f"{removed_duplicates:,}"
    )

    print(
        f"{year}: final Ålesund voyages: "
        f"{len(result):,}"
    )

    return result


# ==================================================================================================
# REPORTING
# ==================================================================================================

def print_summary(
    dataframe: pd.DataFrame,
) -> None:

    print()
    print("=" * 100)
    print("CLEAN DATASET SUMMARY")
    print("=" * 100)

    print(
        f"Rows: "
        f"{len(dataframe):,}"
    )

    print(
        f"Unique voyages: "
        f"{dataframe['seilas_id'].nunique(dropna=True):,}"
    )

    print(
        f"Unique vessel IDs: "
        f"{dataframe['skips_id'].nunique(dropna=True):,}"
    )

    print(
        f"Unique MMSI: "
        f"{dataframe['mmsi_nummer'].nunique(dropna=True):,}"
    )

    print(
        f"Unique IMO: "
        f"{dataframe['imo_nummer'].nunique(dropna=True):,}"
    )

    # ----------------------------------------------------------------------------------------------
    # Source years
    # ----------------------------------------------------------------------------------------------

    print()
    print("ROWS BY YEAR")
    print("-" * 50)

    print(
        dataframe[
            "source_year"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # ----------------------------------------------------------------------------------------------
    # Study-area direction
    # ----------------------------------------------------------------------------------------------

    print()
    print("STUDY AREA EVENT TYPES")
    print("-" * 50)

    departures = int(
        dataframe[
            "departure_in_study_area"
        ].sum()
    )

    arrivals = int(
        dataframe[
            "arrival_in_study_area"
        ].sum()
    )

    internal = int(
        (
            dataframe[
                "departure_in_study_area"
            ]
            &
            dataframe[
                "arrival_in_study_area"
            ]
        )
        .sum()
    )

    print(
        f"Departures from Ålesund: "
        f"{departures:,}"
    )

    print(
        f"Arrivals to Ålesund: "
        f"{arrivals:,}"
    )

    print(
        f"Ålesund -> Ålesund voyages: "
        f"{internal:,}"
    )

    # ----------------------------------------------------------------------------------------------
    # Vessel groups
    # ----------------------------------------------------------------------------------------------

    print()
    print("VESSEL GROUPS")
    print("-" * 50)

    print(
        dataframe[
            "skipsgruppe"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # ----------------------------------------------------------------------------------------------
    # Vessel types
    # ----------------------------------------------------------------------------------------------

    print()
    print("TOP 20 VESSEL TYPES")
    print("-" * 50)

    print(
        dataframe[
            "skipstype"
        ]
        .value_counts(
            dropna=False
        )
        .head(20)
        .to_string()
    )

    # ----------------------------------------------------------------------------------------------
    # Missing percentages
    # ----------------------------------------------------------------------------------------------

    print()
    print("MISSING VALUES (%)")
    print("-" * 50)

    missing = (
        dataframe
        .isna()
        .mean()
        .mul(100)
        .sort_values(
            ascending=False
        )
    )

    print(
        missing
        .round(2)
        .to_string()
    )

    # ----------------------------------------------------------------------------------------------
    # Date ranges
    # ----------------------------------------------------------------------------------------------

    print()
    print("DATE RANGES")
    print("-" * 50)

    departure_min = (
        dataframe["departure_time"].min()
    )

    departure_max = (
        dataframe["departure_time"].max()
    )

    arrival_min = (
        dataframe["arrival_time"].min()
    )

    arrival_max = (
        dataframe["arrival_time"].max()
    )

    print(
        f"Departure time range: "
        f"{departure_min} -> {departure_max}"
    )

    print(
        f"Arrival time range: "
        f"{arrival_min} -> {arrival_max}"
    )

    # ----------------------------------------------------------------------------------------------
    # Voyage duration
    # ----------------------------------------------------------------------------------------------

    print()
    print("VOYAGE DURATION")
    print("-" * 50)

    duration = (
        dataframe[
            "voyage_duration_hours"
        ]
        .dropna()
    )

    if not duration.empty:

        print(
            f"Median duration: "
            f"{duration.median():.2f} h"
        )

        print(
            f"Mean duration: "
            f"{duration.mean():.2f} h"
        )

        print(
            f"95th percentile: "
            f"{duration.quantile(0.95):.2f} h"
        )

    else:

        print(
            "No valid voyage duration "
            "values available."
        )


# ==================================================================================================
# MAIN
# ==================================================================================================

def main() -> None:

    print("=" * 100)
    print("OCEANEYE - PREPARE ÅLESUND VOYAGES")
    print("=" * 100)

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    datasets = []

    for year, file_path in FILES.items():

        if not file_path.exists():

            print(
                f"ERROR: Missing file: "
                f"{file_path}"
            )

            continue

        dataset = process_year(
            year=year,
            file_path=file_path,
        )

        if not dataset.empty:
            datasets.append(
                dataset
            )

    if not datasets:

        raise RuntimeError(
            "No Ålesund data found."
        )

    # ----------------------------------------------------------------------------------------------
    # Combine years
    # ----------------------------------------------------------------------------------------------

    combined = pd.concat(
        datasets,
        ignore_index=True,
    )

    # ----------------------------------------------------------------------------------------------
    # Final duplicate check across all years.
    #
    # We use source_year + seilas_id to avoid assuming the internal
    # voyage ID is globally unique across different annual exports.
    # ----------------------------------------------------------------------------------------------

    before_global_duplicates = len(
        combined
    )

    combined = (
        combined
        .drop_duplicates(
            subset=[
                "source_year",
                "seilas_id",
            ],
            keep="first",
        )
        .reset_index(drop=True)
    )

    removed_global_duplicates = (
        before_global_duplicates
        -
        len(combined)
    )

    print()
    print(
        "Cross-year duplicates removed: "
        f"{removed_global_duplicates:,}"
    )

    # ----------------------------------------------------------------------------------------------
    # Sort chronologically
    # ----------------------------------------------------------------------------------------------

    combined = (
        combined
        .sort_values(
            by=[
                "arrival_time",
                "departure_time",
            ],
            na_position="last",
        )
        .reset_index(drop=True)
    )

    # ----------------------------------------------------------------------------------------------
    # Save CSV
    # ----------------------------------------------------------------------------------------------

    output_csv = (
        PROCESSED_DIR
        / "alesund_voyages_2023_2025.csv"
    )

    combined.to_csv(
        output_csv,
        index=False,
        encoding="utf-8",
    )

    # ----------------------------------------------------------------------------------------------
    # Save ML-primary period separately.
    #
    # This gives us a convenient 2024-2025 file for the next stage
    # while preserving 2023 in the complete cleaned dataset.
    # ----------------------------------------------------------------------------------------------

    primary_ml = (
        combined.loc[
            combined[
                "primary_ml_period"
            ]
        ]
        .copy()
        .reset_index(drop=True)
    )

    primary_output_csv = (
        PROCESSED_DIR
        / "alesund_voyages_2024_2025_ml.csv"
    )

    primary_ml.to_csv(
        primary_output_csv,
        index=False,
        encoding="utf-8",
    )

    # ----------------------------------------------------------------------------------------------
    # Report
    # ----------------------------------------------------------------------------------------------

    print_summary(
        combined
    )

    print()
    print("=" * 100)
    print("OUTPUT FILES")
    print("=" * 100)

    print(
        f"Complete cleaned dataset:\n"
        f"{output_csv}"
    )

    print()

    print(
        f"Primary ML dataset (2024-2025):\n"
        f"{primary_output_csv}"
    )

    print()

    print(
        f"Complete rows: "
        f"{len(combined):,}"
    )

    print(
        f"Primary ML rows: "
        f"{len(primary_ml):,}"
    )


if __name__ == "__main__":
    main()