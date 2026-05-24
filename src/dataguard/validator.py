from datetime import datetime

import polars as pl


def _add_error(
    report,
    column,
    rule,
    message,
    total_failed: int | None = None,
    sample_values: list | None = None,
):
    error = {"column": column, "rule": rule, "message": message}
    if total_failed is not None:
        error["total_failed"] = int(total_failed)
    if sample_values is not None:
        error["sample_offending_values"] = sample_values
    report.append(error)


def _sample_values(series: pl.Series, mask: pl.Series) -> list:
    return series.filter(mask).unique().head(5).to_list()


def validate_dataframe(df: pl.DataFrame, schema: dict) -> list:
    report = []

    for column, rules in schema.items():
        if column not in df.columns:
            _add_error(report, column, "schema", "Column is missing")
            continue

        series = df[column]

        # Type Check
        expected_type = rules.get("type")
        if expected_type:
            casted_col = series.cast(expected_type, strict=False)
            type_mask = series.is_not_null() & casted_col.is_null()
            type_failed = int(type_mask.sum())
            if type_failed > 0:
                _add_error(
                    report,
                    column,
                    "type",
                    "Type mismatch",
                    total_failed=type_failed,
                    sample_values=_sample_values(series, type_mask),
                )

        # Nullability
        if rules.get("nullable") is False and series.null_count() > 0:
            _add_error(report, column, "nullable", "Contains null values")

        # Uniqueness
        if rules.get("unique") is True and not series.is_unique().all():
            _add_error(report, column, "unique", "Contains duplicates")

        # Allowed Values
        if "allowed_values" in rules:
            allowed_mask = (~series.is_in(rules["allowed_values"])).fill_null(False)
            allowed_failed = int(allowed_mask.sum())
            if allowed_failed > 0:
                _add_error(
                    report,
                    column,
                    "allowed_values",
                    "Invalid categorical value",
                    total_failed=allowed_failed,
                    sample_values=_sample_values(series, allowed_mask),
                )

        # Min/Max Value
        if "min_value" in rules:
            min_mask = (series < rules["min_value"]).fill_null(False)
            min_failed = int(min_mask.sum())
            if min_failed > 0:
                _add_error(
                    report,
                    column,
                    "min_value",
                    f"Value below {rules['min_value']}",
                    total_failed=min_failed,
                    sample_values=_sample_values(series, min_mask),
                )

        if "max_value" in rules:
            max_mask = (series > rules["max_value"]).fill_null(False)
            max_failed = int(max_mask.sum())
            if max_failed > 0:
                _add_error(
                    report,
                    column,
                    "max_value",
                    f"Value above {rules['max_value']}",
                    total_failed=max_failed,
                    sample_values=_sample_values(series, max_mask),
                )

        # Regex
        if "regex" in rules:
            regex_mask = (~series.str.contains(rules["regex"])).fill_null(False)
            regex_failed = int(regex_mask.sum())
            if regex_failed > 0:
                _add_error(
                    report,
                    column,
                    "regex",
                    "Pattern mismatch",
                    total_failed=regex_failed,
                    sample_values=_sample_values(series, regex_mask),
                )

        # Date Checks
        if rules.get("no_future_dates") or "date_format" in rules:
            fmt = rules.get("date_format", "%Y-%m-%d")
            date_col = series.str.to_datetime(format=fmt, strict=False)

            if date_col.null_count() > 0:
                _add_error(
                    report, column, "date_format", f"Format mismatch (expected {fmt})"
                )
            elif rules.get("no_future_dates"):
                future_mask = (date_col > datetime.now()).fill_null(False)
                future_failed = int(future_mask.sum())
                if future_failed > 0:
                    _add_error(
                        report,
                        column,
                        "no_future_dates",
                        "Future date found",
                        total_failed=future_failed,
                        sample_values=_sample_values(series, future_mask),
                    )

    return report
