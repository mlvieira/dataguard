from datetime import datetime

import polars as pl


def _add_error(report, column, rule, message, invalid_df=None):
    error = {"column": column, "rule": rule, "message": message}
    if invalid_df is not None:
        error["total_failed"] = invalid_df.height
        error["sample_offending_values"] = invalid_df[column].unique().to_list()[:5]
    report.append(error)


def validate_dataframe(df: pl.DataFrame, schema: dict) -> list:
    report = []

    for column, rules in schema.items():
        if column not in df.columns:
            _add_error(report, column, "schema", "Column is missing")
            continue

        # Type Check
        expected_type = rules.get("type")
        if expected_type:
            casted_col = df[column].cast(expected_type, strict=False)
            failed_rows = df.filter(df[column].is_not_null() & casted_col.is_null())
            if failed_rows.height > 0:
                _add_error(report, column, "type", "Type mismatch", failed_rows)

        # Nullability
        if rules.get("nullable") is False and df[column].null_count() > 0:
            _add_error(report, column, "nullable", "Contains null values")

        # Uniqueness
        if rules.get("unique") is True and not df[column].is_unique().all():
            _add_error(report, column, "unique", "Contains duplicates")

        # Allowed Values
        if "allowed_values" in rules:
            invalid = df.filter(~pl.col(column).is_in(rules["allowed_values"]))
            if invalid.height > 0:
                _add_error(
                    report,
                    column,
                    "allowed_values",
                    "Invalid categorical value",
                    invalid,
                )

        # Min/Max Value
        if "min_value" in rules:
            invalid = df.filter(pl.col(column) < rules["min_value"])
            if invalid.height > 0:
                _add_error(
                    report,
                    column,
                    "min_value",
                    f"Value below {rules['min_value']}",
                    invalid,
                )

        if "max_value" in rules:
            invalid = df.filter(pl.col(column) > rules["max_value"])
            if invalid.height > 0:
                _add_error(
                    report,
                    column,
                    "max_value",
                    f"Value above {rules['max_value']}",
                    invalid,
                )

        # Regex
        if "regex" in rules:
            invalid = df.filter(~pl.col(column).str.contains(rules["regex"]))
            if invalid.height > 0:
                _add_error(report, column, "regex", "Pattern mismatch", invalid)

        # Date Checks
        if rules.get("no_future_dates") or "date_format" in rules:
            fmt = rules.get("date_format", "%Y-%m-%d")
            date_col = df[column].str.to_datetime(format=fmt, strict=False)

            if date_col.null_count() > 0:
                _add_error(
                    report, column, "date_format", f"Format mismatch (expected {fmt})"
                )
            elif rules.get("no_future_dates"):
                future = df.filter(date_col > datetime.now())
                if future.height > 0:
                    _add_error(
                        report, column, "no_future_dates", "Future date found", future
                    )

    return report
