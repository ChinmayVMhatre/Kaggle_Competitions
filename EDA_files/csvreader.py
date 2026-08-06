"""
csv_dataset.py

A small, self-contained helper class for preliminary exploratory data
analysis (EDA) on a CSV file. It covers three common chores:

  1. Loading a CSV into a DataFrame.
  2. Inspecting and handling missing / NaN values.
  3. Detecting and encoding categorical (string) columns.

Plus a handful of convenience EDA methods (summary, describe, correlations,
outlier flags). Designed to be readable and easy to extend rather than
exhaustive.

Requires: pandas, numpy
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Union

import numpy as np
import pandas as pd


class CSVDataset:
    """Wraps a pandas DataFrame loaded from CSV and adds EDA helpers.

    The original data is kept in ``self._original`` so you can always
    call ``reset()`` to undo any cleaning steps.
    """

    def __init__(
        self,
        filepath: Optional[str] = None,
        dataframe: Optional[pd.DataFrame] = None,
        **read_csv_kwargs,
    ):
        """
        Parameters
        ----------
        filepath : str, optional
            Path to a CSV file. Ignored if ``dataframe`` is given.
        dataframe : pd.DataFrame, optional
            Use an existing DataFrame instead of reading from disk.
        **read_csv_kwargs
            Passed straight through to ``pandas.read_csv``
            (e.g. sep=';', na_values=['NA', '?'], encoding='latin-1').
        """
        if dataframe is not None:
            self.df = dataframe.copy()
            self.filepath = None
        elif filepath is not None:
            self.filepath = filepath
            self.df = pd.read_csv(filepath, **read_csv_kwargs)
        else:
            raise ValueError("Provide either `filepath` or `dataframe`.")

        # Keep a pristine copy so cleaning is reversible.
        self._original = self.df.copy()

    # ------------------------------------------------------------------ #
    # Basic dunder / utility
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        rows, cols = self.df.shape
        return f"<CSVDataset rows={rows} cols={cols} source={self.filepath!r}>"

    def __len__(self) -> int:
        return len(self.df)

    def reset(self) -> "CSVDataset":
        """Restore the DataFrame to its state right after loading."""
        self.df = self._original.copy()
        return self

    def head(self, n: int = 5) -> pd.DataFrame:
        return self.df.head(n)

    # ------------------------------------------------------------------ #
    # Column type helpers
    # ------------------------------------------------------------------ #
    def numeric_columns(self) -> list[str]:
        """Columns that pandas treats as numeric."""
        return self.df.select_dtypes(include=[np.number]).columns.tolist()

    def categorical_columns(self, unique_threshold: Optional[int] = None) -> list[str]:
        """Columns that look categorical.

        By default this returns object / string / category dtype columns.
        If ``unique_threshold`` is given, numeric columns with fewer than
        that many distinct values are also flagged (e.g. a 0/1 flag column).
        """
        cat = self.df.select_dtypes(
            include=["object", "string", "category"]
        ).columns.tolist()

        if unique_threshold is not None:
            for col in self.numeric_columns():
                if self.df[col].nunique(dropna=True) < unique_threshold:
                    cat.append(col)
        return cat

    # ------------------------------------------------------------------ #
    # MISSING / NaN VALUE HANDLING
    # ------------------------------------------------------------------ #
    def missing_report(self) -> pd.DataFrame:
        """Per-column count and percentage of missing values, worst first."""
        count = self.df.isna().sum()
        pct = (count / len(self.df) * 100).round(2)
        report = (
            pd.DataFrame({"missing_count": count, "missing_pct": pct})
            .sort_values("missing_count", ascending=False)
        )
        return report[report["missing_count"] > 0]

    def has_missing(self) -> bool:
        return bool(self.df.isna().any().any())

    def drop_missing(
        self,
        axis: int = 0,
        how: str = "any",
        subset: Optional[Sequence[str]] = None,
        thresh: Optional[int] = None,
    ) -> "CSVDataset":
        """Drop rows (axis=0) or columns (axis=1) containing NaNs.

        Mirrors ``DataFrame.dropna``. Returns self for chaining.
        """
        self.df = self.df.dropna(axis=axis, how=how, subset=subset, thresh=thresh)
        return self

    def fill_missing(
        self,
        strategy: str = "mean",
        columns: Optional[Iterable[str]] = None,
        fill_value=None,
    ) -> "CSVDataset":
        """Impute missing values.

        Parameters
        ----------
        strategy : {'mean', 'median', 'mode', 'constant', 'ffill', 'bfill'}
            - mean / median : numeric columns only.
            - mode          : works on any column; uses the most frequent value.
            - constant      : fill with ``fill_value``.
            - ffill / bfill : forward / backward fill.
        columns : iterable of str, optional
            Limit imputation to these columns. Defaults to all columns.
        fill_value :
            Required when strategy == 'constant'.
        """
        cols = list(columns) if columns is not None else self.df.columns.tolist()

        if strategy == "constant":
            if fill_value is None:
                raise ValueError("strategy='constant' needs a `fill_value`.")
            self.df[cols] = self.df[cols].fillna(fill_value)

        elif strategy in ("ffill", "bfill"):
            method = strategy  # 'ffill' or 'bfill'
            self.df[cols] = getattr(self.df[cols], method)()

        elif strategy in ("mean", "median"):
            for col in cols:
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    value = getattr(self.df[col], strategy)()
                    self.df[col] = self.df[col].fillna(value)
            # non-numeric columns are silently skipped for mean/median

        elif strategy == "mode":
            for col in cols:
                mode = self.df[col].mode(dropna=True)
                if not mode.empty:
                    self.df[col] = self.df[col].fillna(mode.iloc[0])

        else:
            raise ValueError(f"Unknown strategy: {strategy!r}")

        return self

    # ------------------------------------------------------------------ #
    # CATEGORICAL VARIABLE HANDLING
    # ------------------------------------------------------------------ #
    def category_summary(self) -> dict[str, pd.Series]:
        """Value counts for each categorical column (handy for a quick look)."""
        return {
            col: self.df[col].value_counts(dropna=False)
            for col in self.categorical_columns()
        }

    def encode_categorical(
        self,
        method: str = "onehot",
        columns: Optional[Iterable[str]] = None,
        drop_first: bool = False,
    ) -> "CSVDataset":
        """Turn string/categorical columns into numbers.

        Parameters
        ----------
        method : {'onehot', 'label'}
            - onehot : one dummy column per category (pandas.get_dummies).
            - label  : map each category to an integer code.
        columns : iterable of str, optional
            Which columns to encode. Defaults to all detected categoricals.
        drop_first : bool
            For one-hot, drop the first level to avoid the dummy trap.

        Note: for 'label' encoding, the mapping learned per column is stored
        in ``self.label_maps`` so you can reverse it later.
        """
        cols = list(columns) if columns is not None else self.categorical_columns()

        if not cols:
            return self  # nothing to do

        if method == "onehot":
            self.df = pd.get_dummies(
                self.df, columns=cols, drop_first=drop_first
            )

        elif method == "label":
            if not hasattr(self, "label_maps"):
                self.label_maps: dict[str, dict] = {}
            for col in cols:
                codes, uniques = pd.factorize(self.df[col])
                # factorize marks NaN as -1; keep it as NaN instead
                codes = pd.Series(codes, index=self.df.index).replace(-1, np.nan)
                self.df[col] = codes
                self.label_maps[col] = dict(enumerate(uniques))

        else:
            raise ValueError(f"Unknown method: {method!r}")

        return self

    # ------------------------------------------------------------------ #
    # EDA CONVENIENCE
    # ------------------------------------------------------------------ #
    def summary(self) -> dict:
        """A one-glance overview dictionary."""
        return {
            "shape": self.df.shape,
            "columns": self.df.columns.tolist(),
            "dtypes": self.df.dtypes.astype(str).to_dict(),
            "numeric_columns": self.numeric_columns(),
            "categorical_columns": self.categorical_columns(),
            "total_missing": int(self.df.isna().sum().sum()),
            "duplicate_rows": int(self.df.duplicated().sum()),
            "memory_kb": round(self.df.memory_usage(deep=True).sum() / 1024, 1),
        }

    def describe(self, include_all: bool = True) -> pd.DataFrame:
        """Descriptive stats. ``include_all`` also covers categorical cols."""
        return self.df.describe(include="all" if include_all else None)

    def correlations(self, method: str = "pearson") -> pd.DataFrame:
        """Correlation matrix across numeric columns."""
        return self.df[self.numeric_columns()].corr(method=method)

    def outlier_flags(self, column: str, k: float = 1.5) -> pd.Series:
        """Boolean mask of IQR-based outliers in a numeric column.

        A value is an outlier if it falls outside
        [Q1 - k*IQR, Q3 + k*IQR]. Default k=1.5 is the usual Tukey rule.
        """
        if column not in self.numeric_columns():
            raise ValueError(f"{column!r} is not numeric.")
        q1, q3 = self.df[column].quantile([0.25, 0.75])
        iqr = q3 - q1
        low, high = q1 - k * iqr, q3 + k * iqr
        return (self.df[column] < low) | (self.df[column] > high)
