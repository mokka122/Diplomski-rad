from pathlib import Path

import pandas as pd


# ==================================================================================================
# PATHS / CONFIGURATION
# ==================================================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

FILES = {
    2020: RAW_DIR / "voyages_2020.csv",
    2021: RAW_DIR / "voyages_2021.csv",
    2022: RAW_DIR / "voyages_2022.csv",
    2023: RAW_DIR / "voyages_2023.csv",
    2024: RAW_DIR / "voyages_2024.csv",
    2025: RAW_DIR / "voyages_2025.csv",
}

CHUNK_SIZE = 100_000

STUDY_AREAS = [
    "Ålesund",
    "Bergen",
    "Tromsø",
    "Stavanger",
    "Kristiansund",
]


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
# NORMALIZATION
# ==================================================================================================

def normalize_identifier(series: pd.Series) -> pd.Series:
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

    return cleaned.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "<NA>": pd.NA,
            "None": pd.NA,
        }
    )


def normalize_numeric(series: pd.Series) -> pd.Series:
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
    cleaned = (
        series
        .astype("string")
        .str.strip()
    )

    return cleaned.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "<NA>": pd.NA,
            "None": pd.NA,
        }
    )


# ==================================================================================================
# GENERAL DATA CLEANING
# ==================================================================================================

def normalize_chunk(
    chunk: pd.DataFrame,
    year: int,
) -> pd.DataFrame:

    chunk = chunk.copy()

    # Text
    for column in TEXT_COLUMNS:
        if column in chunk.columns:
            chunk[column] = normalize_text(
                chunk[column]
            )

    # Identifiers
    for column in IDENTIFIER_COLUMNS:
        if column in chunk.columns:
            chunk[column] = normalize_identifier(
                chunk[column]
            )

    # Numeric vessel attributes
    for column in NUMERIC_COLUMNS:
        if column in chunk.columns:
            chunk[column] = normalize_numeric(
                chunk[column]
            )

    # Timestamps
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

    chunk["source_year"] = year

    # ----------------------------------------------------------------------------------------------
    # MMSI validation
    # ----------------------------------------------------------------------------------------------

    valid_mmsi = (
        chunk["mmsi_nummer"]
        .str.fullmatch(
            r"\d{9}",
            na=False,
        )
    )

    invalid_mmsi = (
        chunk["mmsi_nummer"].notna()
        &
        ~valid_mmsi
    )

    chunk.loc[
        invalid_mmsi,
        "mmsi_nummer"
    ] = pd.NA

    # ----------------------------------------------------------------------------------------------
    # IMO format validation
    # ----------------------------------------------------------------------------------------------

    valid_imo = (
        chunk["imo_nummer"]
        .str.fullmatch(
            r"\d{7}",
            na=False,
        )
    )

    invalid_imo = (
        chunk["imo_nummer"].notna()
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
        invalid = (
            chunk["lengde"].notna()
            &
            (
                (chunk["lengde"] <= 0)
                |
                (chunk["lengde"] > 500)
            )
        )

        chunk.loc[
            invalid,
            "lengde"
        ] = pd.NA

    if "bredde" in chunk.columns:
        invalid = (
            chunk["bredde"].notna()
            &
            (
                (chunk["bredde"] <= 0)
                |
                (chunk["bredde"] > 100)
            )
        )

        chunk.loc[
            invalid,
            "bredde"
        ] = pd.NA

    if "dypgaaende" in chunk.columns:
        invalid = (
            chunk["dypgaaende"].notna()
            &
            (
                (chunk["dypgaaende"] < 0)
                |
                (chunk["dypgaaende"] > 30)
            )
        )

        chunk.loc[
            invalid,
            "dypgaaende"
        ] = pd.NA

    if "byggeaar" in chunk.columns:
        invalid = (
            chunk["byggeaar"].notna()
            &
            (
                (chunk["byggeaar"] < 1800)
                |
                (chunk["byggeaar"] > year)
            )
        )

        chunk.loc[
            invalid,
            "byggeaar"
        ] = pd.NA

    # ----------------------------------------------------------------------------------------------
    # Voyage duration
    #
    # NOTE:
    # departure_time is based on estimated departure time (ETD),
    # therefore this is only a derived analytical value.
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

    chunk.loc[
        chunk["voyage_duration_hours"] < 0,
        "voyage_duration_hours"
    ] = pd.NA

    return chunk


# ==================================================================================================
# EXPAND VOYAGES TO STUDY-AREA OBSERVATIONS
# ==================================================================================================

def expand_study_areas(
    chunk: pd.DataFrame,
) -> pd.DataFrame:
    """
    Creates one row per voyage + relevant study area.

    Example:

        Bergen -> Ålesund

    becomes:

        row 1:
            study_area = Bergen
            departure_in_study_area = True
            arrival_in_study_area = False

        row 2:
            study_area = Ålesund
            departure_in_study_area = False
            arrival_in_study_area = True

    This is required because one voyage can contribute an event
    to two different study areas.
    """

    area_datasets = []

    for study_area in STUDY_AREAS:

        departure_in_area = (
            chunk[
                "kommunenavn_avgang"
            ].eq(study_area)
            &
            chunk[
                "landkode_avgang_totegn"
            ].eq("NO")
        )

        arrival_in_area = (
            chunk[
                "kommunenavn_ankomst"
            ].eq(study_area)
            &
            chunk[
                "landkode_ankomst_totegn"
            ].eq("NO")
        )

        departure_in_area = (
            departure_in_area
            .fillna(False)
            .astype(bool)
        )

        arrival_in_area = (
            arrival_in_area
            .fillna(False)
            .astype(bool)
        )

        relevant = (
            departure_in_area
            |
            arrival_in_area
        )

        area_chunk = (
            chunk.loc[
                relevant
            ]
            .copy()
        )

        if area_chunk.empty:
            continue

        area_chunk[
            "study_area"
        ] = study_area

        area_chunk[
            "departure_in_study_area"
        ] = (
            departure_in_area
            .loc[area_chunk.index]
            .fillna(False)
            .astype(bool)
        )

        area_chunk[
            "arrival_in_study_area"
        ] = (
            arrival_in_area
            .loc[area_chunk.index]
            .fillna(False)
            .astype(bool)
        )

        area_datasets.append(
            area_chunk
        )

    if not area_datasets:
        return pd.DataFrame()

    return pd.concat(
        area_datasets,
        ignore_index=True,
    )


# ==================================================================================================
# PROCESS ONE YEAR
# ==================================================================================================

def process_year(
    year: int,
    file_path: Path,
) -> pd.DataFrame:

    print()
    print("=" * 100)
    print(
        f"PROCESSING MULTI-AREA DATA - {year}"
    )
    print("=" * 100)

    processed_chunks = []

    total_read = 0
    total_area_rows = 0

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

        chunk = normalize_chunk(
            chunk=chunk,
            year=year,
        )

        expanded = expand_study_areas(
            chunk
        )

        total_area_rows += len(
            expanded
        )

        if not expanded.empty:
            processed_chunks.append(
                expanded
            )

        print(
            f"{year}: "
            f"chunk={chunk_number} | "
            f"read={total_read:,} | "
            f"study-area rows={total_area_rows:,}"
        )

    if not processed_chunks:

        print(
            f"WARNING: No selected study-area "
            f"records found for {year}."
        )

        return pd.DataFrame()

    result = pd.concat(
        processed_chunks,
        ignore_index=True,
    )

    # ----------------------------------------------------------------------------------------------
    # Duplicate definition:
    #
    # Same voyage can legitimately appear in two study areas.
    # Therefore we deduplicate by:
    #
    # study_area + seilas_id
    # ----------------------------------------------------------------------------------------------

    before_duplicates = len(
        result
    )

    result = (
        result
        .drop_duplicates(
            subset=[
                "study_area",
                "seilas_id",
            ],
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
        f"{year}: final voyage-area rows: "
        f"{len(result):,}"
    )

    return result


# ==================================================================================================
# SUMMARY
# ==================================================================================================

def print_summary(
    dataframe: pd.DataFrame,
) -> None:

    print()
    print("=" * 100)
    print("MULTI-AREA CLEAN DATASET SUMMARY")
    print("=" * 100)

    print(
        f"Voyage-area rows: "
        f"{len(dataframe):,}"
    )

    print(
        f"Unique voyages: "
        f"{dataframe['seilas_id'].nunique(dropna=True):,}"
    )

    print(
        f"Unique MMSI: "
        f"{dataframe['mmsi_nummer'].nunique(dropna=True):,}"
    )

    print()
    print("ROWS BY YEAR")
    print("-" * 70)

    print(
        dataframe[
            "source_year"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print()
    print("ROWS BY STUDY AREA")
    print("-" * 70)

    print(
        dataframe[
            "study_area"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print("ROWS BY STUDY AREA AND YEAR")
    print("-" * 70)

    area_year = (
        dataframe
        .groupby(
            [
                "study_area",
                "source_year",
            ]
        )
        .size()
        .unstack(
            fill_value=0
        )
    )

    print(
        area_year.to_string()
    )

    print()
    print("UNIQUE MMSI BY STUDY AREA")
    print("-" * 70)

    print(
        dataframe
        .groupby(
            "study_area"
        )[
            "mmsi_nummer"
        ]
        .nunique()
        .sort_values(
            ascending=False
        )
        .to_string()
    )

    print()
    print("ARRIVAL / DEPARTURE FLAGS BY STUDY AREA")
    print("-" * 70)

    event_summary = (
        dataframe
        .groupby(
            "study_area"
        )
        .agg(
            departures=(
                "departure_in_study_area",
                "sum",
            ),
            arrivals=(
                "arrival_in_study_area",
                "sum",
            ),
        )
    )

    print(
        event_summary.to_string()
    )

    print()
    print("DATE RANGE")
    print("-" * 70)

    print(
        "Departure: "
        f"{dataframe['departure_time'].min()} "
        f"-> "
        f"{dataframe['departure_time'].max()}"
    )

    print(
        "Arrival:   "
        f"{dataframe['arrival_time'].min()} "
        f"-> "
        f"{dataframe['arrival_time'].max()}"
    )

    print()
    print("VESSEL GROUPS")
    print("-" * 70)

    print(
        dataframe[
            "skipsgruppe"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )


# ==================================================================================================
# MAIN
# ==================================================================================================

def main() -> None:

    print("=" * 100)
    print(
        "OCEANEYE - PREPARE MULTI-AREA VOYAGES"
    )
    print("=" * 100)

    print()
    print(
        "Study areas:"
    )

    for study_area in STUDY_AREAS:
        print(
            f"  - {study_area}"
        )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    datasets = []

    for year, file_path in FILES.items():

        if not file_path.exists():

            raise FileNotFoundError(
                f"Missing raw dataset: "
                f"{file_path}"
            )

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
            "No multi-area data found."
        )

    # ----------------------------------------------------------------------------------------------
    # Combine all years
    # ----------------------------------------------------------------------------------------------

    combined = pd.concat(
        datasets,
        ignore_index=True,
    )

    # ----------------------------------------------------------------------------------------------
    # Cross-year duplicate safety.
    #
    # source_year is included because the internal voyage ID
    # is not assumed to be globally unique between annual exports.
    # ----------------------------------------------------------------------------------------------

    before_duplicates = len(
        combined
    )

    combined = (
        combined
        .drop_duplicates(
            subset=[
                "source_year",
                "study_area",
                "seilas_id",
            ],
            keep="first",
        )
        .reset_index(drop=True)
    )

    removed_duplicates = (
        before_duplicates
        -
        len(combined)
    )

    print()
    print(
        "Cross-year duplicate voyage-area rows removed: "
        f"{removed_duplicates:,}"
    )

    # ----------------------------------------------------------------------------------------------
    # Chronological ordering
    # ----------------------------------------------------------------------------------------------

    combined = (
        combined
        .sort_values(
            by=[
                "study_area",
                "source_year",
                "arrival_time",
                "departure_time",
            ],
            na_position="last",
        )
        .reset_index(drop=True)
    )

    # ----------------------------------------------------------------------------------------------
    # Save
    # ----------------------------------------------------------------------------------------------

    output_file = (
        PROCESSED_DIR
        / "multi_area_voyages_2020_2025.csv"
    )

    combined.to_csv(
        output_file,
        index=False,
        encoding="utf-8",
    )

    print_summary(
        combined
    )

    print()
    print("=" * 100)
    print("OUTPUT FILE")
    print("=" * 100)

    print(
        output_file
    )

    print()

    print(
        f"Final voyage-area rows: "
        f"{len(combined):,}"
    )


if __name__ == "__main__":
    main()