from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Expose Python built-ins that templates need
templates.env.globals["str"] = str
templates.env.globals["int"] = int
