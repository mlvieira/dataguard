from datetime import datetime

import polars as pl


def validate_dataframe(df: pl.DataFrame, schema: dict) -> bool:
    is_valid = True

    for column, rules in schema.items():
        if column not in df.columns:
            print(f"FAILED: Missing column '{column}'")
            return False

        expected_type = rules.get("type")

        if expected_type is None:
            print(f"ERROR: No valid Polars type found for column '{column}'")
            is_valid = False
            continue

        try:
            casted_col = df[column].cast(expected_type, strict=False)

            failed_rows = df.filter(df[column].is_not_null() & casted_col.is_null())

            if failed_rows.height > 0:
                print(
                    f"FAILED: '{column}' contains {failed_rows.height} values that do not match type."
                )
                is_valid = False
        except Exception as e:
            print(f"ERROR: Could not cast column '{column}': {e}")
            is_valid = False

        # Check Nullability
        if rules.get("nullable") is False:
            null_count = df[column].null_count()
            if null_count > 0:
                print(f"FAILED: '{column}' has {null_count} nulls but is non-nullable.")
                is_valid = False

        # Check Uniqueness
        if rules.get("unique") is True:
            if not df[column].is_unique().all():
                print(f"FAILED: '{column}' contains duplicate values.")
                is_valid = False

        # Check if column only contains allowed values
        allowed_values = rules.get("allowed_values")
        if allowed_values:
            invalid_rows = df.filter(~pl.col(column).is_in(allowed_values))

            if invalid_rows.height > 0:
                print(
                    f"FAILED: '{column}' contains {invalid_rows.height} invalid values."
                )
                offending_values = invalid_rows[column].unique().to_list()
                print(f"  -> Found invalid values: {offending_values}")
                is_valid = False

        # Check if column only has values below X value
        min_value = rules.get("min_value")
        if min_value:
            invalid_rows = df.filter(pl.col(column) < min_value)

            if invalid_rows.height > 0:
                print(
                    f"FAILED: '{column}' contains {invalid_rows.height} invalid values."
                )
                offending_values = invalid_rows[column].unique().to_list()
                print(f"  -> Found invalid values: {offending_values}")
                is_valid = False

        # Check if column only has values above X value
        max_value = rules.get("max_value")
        if max_value:
            invalid_rows = df.filter(pl.col(column) > max_value)

            if invalid_rows.height > 0:
                print(
                    f"FAILED: '{column}' contains {invalid_rows.height} invalid values."
                )
                offending_values = invalid_rows[column].unique().to_list()
                print(f"  -> Found invalid values: {offending_values}")
                is_valid = False

        # Check if column matches a regex pattern
        regex_value = rules.get("regex")
        if regex_value:
            invalid_rows = df.filter(~pl.col(column).str.contains(regex_value))

            if invalid_rows.height > 0:
                print(
                    f"FAILED: '{column}' contains {invalid_rows.height} invalid values."
                )
                offending_values = invalid_rows[column].unique().to_list()
                print(f"  -> Found invalid values: {offending_values}")
                is_valid = False

        if rules.get("no_future_dates") or rules.get("date_format"):
            fmt_date = rules.get("date_format", "%Y-%m-%d")

            date_col = df[column].str.to_datetime(format=fmt_date, strict=False)

            if date_col.null_count() > 0:
                print(
                    f"FAILED: '{column}' has values that don't match format '{fmt_date}'"
                )
                is_valid = False

            if rules.get("no_future_dates"):
                now = datetime.now()
                future_rows = df.filter(date_col > now)

                if future_rows.height > 0:
                    print(
                        f"FAILED: '{column}' contains {future_rows.height} future dates."
                    )
                    is_valid = False

    return is_valid
