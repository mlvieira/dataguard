import json
from datetime import datetime

import polars as pl
import typer

from dataguard.schemas import load_schema
from dataguard.validator import validate_dataframe

app = typer.Typer()


@app.command()
def validate(
    input_file: str = typer.Option(..., "--input-file", "-i", help="Path to CSV file"),
    schema_file: str = typer.Option(
        ..., "--schema-file", "-s", help="Path to YAML schema"
    ),
    output: str = typer.Option(None, "--output", "-o", help="Path to save JSON report"),
):
    typer.echo(f"Validating {input_file} against {schema_file}...")

    schema = load_schema(schema_file)
    cols_to_check = list(schema.keys())

    df = pl.scan_csv(input_file).select(cols_to_check).collect()
    errors = validate_dataframe(df, schema)

    report_data = {
        "timestamp": datetime.now().isoformat(),
        "file": input_file,
        "status": "PASSED" if not errors else "FAILED",
        "errors": errors,
    }

    if output:
        with open(output, "w") as f:
            json.dump(report_data, f, indent=2)
        typer.secho(f"Report saved to {output}", fg=typer.colors.BLUE)
    else:
        typer.echo(json.dumps(report_data, indent=2))


def main():
    app()


if __name__ == "__main__":
    main()
