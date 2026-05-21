"""Admin CLI helpers — run with `python -m app.admin.cli`."""
import bcrypt
import typer

app_admin_cli = typer.Typer(name="admin", help="Kyros admin CLI utilities.")


@app_admin_cli.command("set-password")
def set_password() -> None:
    """Prompt for a password and print its bcrypt hash to stdout.

    Copy the hash into ADMIN_PASSWORD_HASH in your .env file.
    """
    password = typer.prompt("New admin password", hide_input=True, confirmation_prompt=True)
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    typer.echo(f"\nAdd this to your .env:\n\nADMIN_PASSWORD_HASH={hashed}\n")


if __name__ == "__main__":
    app_admin_cli()
