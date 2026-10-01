from pathlib import Path
import typer
from rich.console import Console
from src.extractor import ClaimsExtractor, ExtractionFailureError
from src.evaluator import Evaluator  # Adjust function name to match your evaluator.py

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


@app.command()
def evaluate(
    dataset_path: Path = typer.Option(
        Path("tests/evaluator_test_data"),
        "--dataset",
        "-d",
        help="Path to evaluation dataset or directory",
        exists=True,
    ),
    output_report: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional path to save evaluation report (JSON/CSV)",
    ),
):
    """Run extraction accuracy, hallucination, and scoring benchmarks."""
    console.print(f"[bold green]Running evaluation against:[/bold green] {dataset_path}")
    
    try:
        results = Evaluator()
        
        # If your evaluation function returns summary metrics:
        if results:
            console.print("[bold cyan]Evaluation Complete:[/bold cyan]")
            console.print(results)
            
        if output_report:
            console.print(f"[dim]Report saved to {output_report}[/dim]")

    except Exception as exc:
        console.print(f"[bold red]Evaluation failed:[/bold red] {exc}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()