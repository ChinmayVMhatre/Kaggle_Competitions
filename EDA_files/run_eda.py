"""
run_eda.py

Example script showing how to use the CSVDataset class from csv_dataset.py.
Run it from the same folder:

    python run_eda.py

It loads employees.csv, walks through a quick EDA, then cleans and encodes
the data.
"""

from csv_dataset import CSVDataset


def section(title: str) -> None:
    """Print a small header so the output is easy to scan."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main() -> None:
    # 1. Load the file. `na_values` shows how to flag extra missing markers;
    #    empty cells are treated as NaN automatically.
    ds = CSVDataset("employees.csv", na_values=["", "NA", "?"])

    section("OVERVIEW")
    print(ds)                       # <CSVDataset rows=... cols=...>
    print(ds.head(3))               # first few rows

    section("SUMMARY")
    for key, value in ds.summary().items():
        print(f"{key:>20}: {value}")

    section("MISSING VALUE REPORT")
    print(ds.missing_report())

    section("CATEGORICAL COLUMNS")
    print("Detected:", ds.categorical_columns())
    for col, counts in ds.category_summary().items():
        print(f"\n[{col}]")
        print(counts)

    section("DESCRIPTIVE STATS")
    print(ds.describe())

    section("CORRELATIONS (numeric)")
    print(ds.correlations().round(2))

    section("OUTLIERS IN 'age' (Tukey IQR)")
    flags = ds.outlier_flags("age")
    print("Outlier rows:", ds.df.loc[flags, "age"].tolist())

    # 2. Clean it up.
    #    - numeric gaps -> median
    #    - categorical gaps -> most frequent value
    section("CLEANING")
    numeric = ds.numeric_columns()
    categorical = ds.categorical_columns()

    ds.fill_missing(strategy="median", columns=numeric)
    ds.fill_missing(strategy="mode", columns=categorical)
    print(f"Missing values remaining: {ds.df.isna().sum().sum()}")

    # 3. Encode categoricals two different ways, on fresh copies each time.
    section("ONE-HOT ENCODING")
    onehot = CSVDataset(dataframe=ds.df)
    onehot.encode_categorical(method="onehot", drop_first=True)
    print(onehot.df.head())

    section("LABEL ENCODING")
    labeled = CSVDataset(dataframe=ds.df)
    labeled.encode_categorical(method="label")
    print(labeled.df.head())
    print("\nLabel maps (code -> original value):")
    for col, mapping in labeled.label_maps.items():
        print(f"  {col}: {mapping}")

    # 4. reset() proves the original data is still intact.
    section("RESET DEMO")
    print("Before reset, salary NaNs:", ds.df["salary"].isna().sum())
    ds.reset()
    print("After reset, salary NaNs :", ds.df["salary"].isna().sum())


if __name__ == "__main__":
    main()
