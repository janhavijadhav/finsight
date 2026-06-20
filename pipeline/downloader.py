import requests
import os
import time
from pathlib import Path

COMPANIES = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "NVDA": "0001045810",
    "TSLA": "0001318605",
    "JPM":  "0000019617",
    "META": "0001326801",
}

HEADERS_DATA = {
    "User-Agent": "Janhavi Jadhav janhavijadhav@gmail.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov"
}

HEADERS_WWW = {
    "User-Agent": "Janhavi Jadhav janhavijadhav@gmail.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
}

def get_10k_filings(cik: str, ticker: str) -> list:
    """
    Fetches the list of 10-K filings for a company.
    Prints what it finds so we can debug if needed.
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    print(f"  Fetching filing list from: {url}")
    
    response = requests.get(url, headers=HEADERS_DATA)
    response.raise_for_status()
    data = response.json()
    
    filings = data["filings"]["recent"]
    
    # Print first few form types so we can see what's available
    print(f"  Recent form types: {filings['form'][:10]}")
    
    results = []
    for i, form in enumerate(filings["form"]):
        if form == "10-K":
            accession_raw = filings["accessionNumber"][i]        # e.g. 0000320193-24-000123
            accession_clean = accession_raw.replace("-", "")     # e.g. 0000320193240000123
            primary_doc = filings["primaryDocument"][i]
            filing_date = filings["filingDate"][i]
            
            print(f"  Found 10-K: date={filing_date}, doc={primary_doc}")
            
            results.append({
                "date": filing_date,
                "accession_raw": accession_raw,
                "accession_clean": accession_clean,
                "primary_doc": primary_doc,
                "cik_int": str(int(cik)),  # remove leading zeros for URL
            })
            
            if len(results) >= 2:
                break
    
    return results

def download_single_filing(filing: dict, ticker: str, output_dir: Path):
    """
    Downloads one filing. Tries the primary document first,
    then falls back to the full filing index if that fails.
    """
    cik_int = filing["cik_int"]
    accession_clean = filing["accession_clean"]
    primary_doc = filing["primary_doc"]
    date = filing["date"]
    
    # Primary document URL
    primary_url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_int}/{accession_clean}/{primary_doc}"
    )
    
    print(f"  Trying: {primary_url}")
    
    try:
        response = requests.get(primary_url, headers=HEADERS_WWW, timeout=30)
        response.raise_for_status()
        
        # Determine extension from content type or URL
        content_type = response.headers.get("Content-Type", "")
        if "pdf" in content_type or primary_doc.endswith(".pdf"):
            ext = "pdf"
        elif "htm" in content_type or primary_doc.endswith(".htm"):
            ext = "htm"
        else:
            ext = primary_doc.split(".")[-1] if "." in primary_doc else "txt"
        
        # Save the file
        save_dir = output_dir / ticker
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / f"{date}.{ext}"
        
        with open(save_path, "wb") as f:
            f.write(response.content)
        
        size_kb = len(response.content) / 1024
        print(f"  Saved: {save_path} ({size_kb:.0f} KB)")
        return True
        
    except Exception as e:
        print(f"  Primary doc failed: {e}")
        
        # Fallback — download the filing index page instead
        index_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_int}/{accession_clean}/{accession_clean}-index.htm"
        )
        print(f"  Trying index fallback: {index_url}")
        
        try:
            response = requests.get(index_url, headers=HEADERS_WWW, timeout=30)
            response.raise_for_status()
            
            save_dir = output_dir / ticker
            save_dir.mkdir(parents=True, exist_ok=True)
            save_path = save_dir / f"{date}_index.htm"
            
            with open(save_path, "wb") as f:
                f.write(response.content)
            
            size_kb = len(response.content) / 1024
            print(f"  Saved index: {save_path} ({size_kb:.0f} KB)")
            return True
            
        except Exception as e2:
            print(f"  Index fallback also failed: {e2}")
            return False

def download_filings(output_dir: str = "data/raw"):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    
    for ticker, cik in COMPANIES.items():
        print(f"\n{'='*40}")
        print(f"Processing {ticker} (CIK: {cik})")
        
        try:
            filings = get_10k_filings(cik, ticker)
            
            if not filings:
                print(f"  No 10-K filings found for {ticker}")
                continue
            
            for filing in filings:
                ok = download_single_filing(filing, ticker, output_path)
                if ok:
                    success_count += 1
                time.sleep(0.6)  # respect SEC rate limits
                
        except Exception as e:
            print(f"  Error processing {ticker}: {e}")
    
    print(f"\n{'='*40}")
    print(f"Done. Successfully downloaded {success_count} filing(s).")
    print(f"Check: ls data/raw/")

if __name__ == "__main__":
    download_filings()