from pathlib import Path
import typer
from rich.console import Console
from src.extractor import ClaimsExtractor, ExtractionFailureError

app = typer.Typer()
console = Console()

@app.command()
def extract(
    file_path: Path = typer.Argument(..., help="Path to raw text document", exists=True),
    max_retries: int = typer.Option(3, help="Max retry cycles")
):
    """Parse unstructured medical records into validated JSON."""
    raw_text = file_path.read_text(encoding="utf-8")
    extractor = ClaimsExtractor(max_retries=max_retries)

    try:
        record = extractor.extract(raw_text)
        console.print_json(record.model_dump_json(indent=2))
    except ExtractionFailureError as exc:
        console.print("[bold red]Extraction Aborted:[/bold red]", exc)
        for err in exc.errors:
            console.print(f"[yellow]- {err}[/yellow]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()