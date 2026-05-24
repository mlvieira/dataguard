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
):
    typer.echo(f"Validating {input_file} against {schema_file}...")

    schema = load_schema(schema_file)
    cols_to_check = list(schema.keys())

    df = pl.scan_csv(input_file).select(cols_to_check).collect()
    if validate_dataframe(df, schema):
        typer.secho("Success: Data matches schema!", fg=typer.colors.GREEN)
    else:
        raise typer.Exit(code=1)


def main():
    app()


if __name__ == "__main__":
    main()
