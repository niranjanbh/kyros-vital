import json

import typer

from app.admin.cli import app_admin_cli

app_cli = typer.Typer(name="kyros", help="Kyros backend CLI.")
app_cli.add_typer(app_admin_cli, name="admin")


@app_cli.command()
def export_openapi(
    output: str = typer.Option("openapi.json", "--output", "-o", help="Output file path."),
) -> None:
    """Generate and write the OpenAPI schema to disk."""
    from app.main import app as fastapi_app

    schema = fastapi_app.openapi()
    with open(output, "w") as f:
        json.dump(schema, f, indent=2)
    typer.echo(f"OpenAPI schema written to {output}")


@app_cli.command()
def seed() -> None:
    """Run the seed script against the configured database."""
    import asyncio

    import scripts.seed as seed_module

    asyncio.run(seed_module.main())


if __name__ == "__main__":
    app_cli()
