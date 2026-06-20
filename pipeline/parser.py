from bs4 import BeautifulSoup
from pathlib import Path
import json
import re

def clean_text(text: str) -> str:
    """Clean up messy HTML-extracted text."""
    text = re.sub(r'\n{3,}', '\n\n', text)   # max 2 consecutive newlines
    text = re.sub(r'[ \t]+', ' ', text)        # collapse spaces
    text = re.sub(r' \n', '\n', text)           # remove trailing spaces
    text = text.strip()
    return text

def parse_html_filing(html_path: Path) -> dict:
    """
    Extracts clean text from an SEC 10-K HTML file.
    Strips all HTML tags, scripts, styles, and XBRL metadata.
    """
    ticker = html_path.parent.name  # folder name = ticker

    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_html = f.read()

    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove noise — scripts, styles, hidden XBRL tags
    for tag in soup(["script", "style", "ix:header", "ix:hidden"]):
        tag.decompose()

    # Extract plain text
    text = soup.get_text(separator="\n")
    text = clean_text(text)

    return {
        "ticker": ticker,
        "file_path": str(html_path),
        "text": text,
        "char_count": len(text)
    }

def parse_all_filings(raw_dir: str = "data/raw", output_dir: str = "data/processed"):
    raw_path = Path(raw_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    html_files = list(raw_path.rglob("*.html")) + list(raw_path.rglob("*.htm"))

    print(f"Found {len(html_files)} filing(s) to parse")

    for html_path in html_files:
        print(f"Parsing {html_path.parent.name}...")
        try:
            result = parse_html_filing(html_path)

            out_file = output_path / f"{result['ticker']}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"  Saved: {out_file.name} ({result['char_count']:,} characters)")

        except Exception as e:
            print(f"  Error parsing {html_path.name}: {e}")

if __name__ == "__main__":
    parse_all_filings()