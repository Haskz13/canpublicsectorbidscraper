"""
CanadaBuys Open Data Opportunity Monitor
=========================================
Downloads the official Government of Canada "Standing Offers and Supply
Arrangements" and "Tender Notice" datasets from the Open Government portal,
then filters for training/certification-related opportunities relevant to
The Knowledge Academy.

Data source: https://open.canada.ca  (Open Government Licence - Canada)
"""

import csv
import io
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tka_pipeline.sqlite"

# Official Open Data CSV endpoints (English)
# These are the bulk-download CSVs published under the Open Government Licence.
CANADABUYS_TENDER_CSV = (
    "https://buyandsell.gc.ca/procurement-data/csv/tender"
)

# Keywords that signal training / certification relevance
TRAINING_KEYWORDS = [
    "training",
    "professional development",
    "learning",
    "certification",
    "prince2",
    "itil",
    "pmp",
    "project management",
    "cyber security",
    "cybersecurity",
    "agile",
    "scrum",
    "cissp",
    "cism",
    "digital transformation",
    "modernization",
    "professional services",
]

# Departments of strategic interest
PRIORITY_DEPARTMENTS = [
    "Shared Services Canada",
    "SSC",
    "Department of National Defence",
    "DND",
    "Canada Border Services Agency",
    "CBSA",
    "Treasury Board",
    "TBS",
    "Public Services and Procurement Canada",
    "PSPC",
    "Employment and Social Development Canada",
    "ESDC",
    "Immigration, Refugees and Citizenship Canada",
    "IRCC",
    "Canada Revenue Agency",
    "CRA",
    "Health Canada",
    "Transport Canada",
    "Innovation, Science and Economic Development",
    "ISED",
]


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create the pipeline database and tables if they don't exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            source              TEXT NOT NULL DEFAULT 'CanadaBuys',
            tender_id           TEXT,
            title               TEXT,
            department          TEXT,
            branch              TEXT,
            description         TEXT,
            published_date      TEXT,
            closing_date        TEXT,
            estimated_value     REAL,
            signal_type         TEXT,
            matched_keywords    TEXT,
            priority_dept       INTEGER DEFAULT 0,
            revenue_score       INTEGER DEFAULT 0,
            projected_revenue   REAL DEFAULT 0,
            recommended_solution TEXT,
            consultative_brief  TEXT,
            status              TEXT DEFAULT 'new',
            created_at          TEXT DEFAULT (datetime('now')),
            UNIQUE(tender_id, source)
        );

        CREATE TABLE IF NOT EXISTS demand_signals (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            department          TEXT,
            signal_source       TEXT,
            signal_description  TEXT,
            hiring_count        INTEGER DEFAULT 0,
            signal_type         TEXT,
            created_at          TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS contact_research (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id      INTEGER,
            department          TEXT,
            branch              TEXT,
            role_title          TEXT,
            public_office_phone TEXT,
            email_syntax_note   TEXT,
            source_url          TEXT,
            created_at          TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
        );
    """)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# CSV download & parsing
# ---------------------------------------------------------------------------

def download_csv(url: str) -> list[dict]:
    """Download a CSV from a URL and return rows as dicts."""
    print(f"[*] Downloading: {url}")
    req = Request(url, headers={"User-Agent": "TKA-Pipeline-Monitor/1.0"})
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8-sig", errors="replace")
    except URLError as e:
        print(f"[!] Download failed: {e}")
        print("    You can manually download the CSV from CanadaBuys Open Data")
        print("    and place it at: data/tender_notices.csv")
        return []

    # Normalize line endings to handle embedded newlines in fields
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    reader = csv.DictReader(io.StringIO(raw, newline=""))
    rows = []
    for row in reader:
        try:
            rows.append(row)
        except csv.Error:
            continue  # skip malformed rows
    print(f"    -> {len(rows)} rows downloaded")
    return rows


def load_local_csv(path: str) -> list[dict]:
    """Fallback: load a locally saved CSV."""
    p = Path(path)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Filtering logic
# ---------------------------------------------------------------------------

def matches_keywords(text: str) -> list[str]:
    """Return list of matched training keywords found in text."""
    if not text:
        return []
    lower = text.lower()
    return [kw for kw in TRAINING_KEYWORDS if kw in lower]


def is_priority_department(dept_name: str) -> bool:
    """Check if department is on our strategic priority list."""
    if not dept_name:
        return False
    lower = dept_name.lower()
    return any(pd.lower() in lower for pd in PRIORITY_DEPARTMENTS)


def filter_opportunities(rows: list[dict]) -> list[dict]:
    """Filter tender rows for training-related opportunities."""
    results = []
    for row in rows:
        # Combine searchable fields (column names vary by dataset)
        searchable = " ".join(
            str(row.get(col, ""))
            for col in row.keys()
        )
        matched = matches_keywords(searchable)
        if matched:
            row["_matched_keywords"] = matched
            row["_priority_dept"] = is_priority_department(
                row.get("department", row.get("owner_org", ""))
            )
            results.append(row)
    print(f"[*] Filtered to {len(results)} training-related opportunities")
    return results


# ---------------------------------------------------------------------------
# Revenue scoring
# ---------------------------------------------------------------------------

def score_opportunity(row: dict) -> dict:
    """
    Apply the TKA revenue scoring model:
      10 = Active RFP + priority dept           -> $25k+
       8 = Active RFP, non-priority             -> $15k-$25k
       7 = Priority dept, general match          -> $10k-$15k
       5 = General match                         -> $5k+
    Only leads scoring >= 7 are kept for the final report.
    """
    score = 5  # baseline
    keywords = row.get("_matched_keywords", [])
    priority = row.get("_priority_dept", False)

    # Boost for high-value certification keywords
    high_value_kw = {"prince2", "itil", "pmp", "cissp", "cism", "cyber security"}
    if any(kw in high_value_kw for kw in keywords):
        score += 2

    # Boost for priority departments
    if priority:
        score += 1

    # Boost for multiple keyword matches (strong signal)
    if len(keywords) >= 3:
        score += 1

    score = min(score, 10)

    # Revenue projection
    if score >= 9:
        projected = 25000
        solution = "Full certification program (PRINCE2 + PMP cohort)"
    elif score >= 7:
        projected = 15000
        solution = "Targeted certification (group booking, 5-day intensive)"
    else:
        projected = 5000
        solution = "Individual certification seats or Lunch & Learn intro"

    row["_score"] = score
    row["_projected_revenue"] = projected
    row["_solution"] = solution
    return row


def generate_consultative_brief(row: dict) -> str:
    """
    Create a short consultative brief connecting the department's
    public mandate to TKA's training capabilities.
    """
    dept = row.get("department", row.get("owner_org", "Unknown Department"))
    keywords = row.get("_matched_keywords", [])
    title = row.get("title", row.get("description", ""))[:120]

    if "cyber" in " ".join(keywords).lower():
        return (
            f"{dept} is investing in cyber resilience. TKA can deliver "
            f"CISSP/CISM certification for their security team in a 5-day "
            f"intensive, aligned to their requirement: '{title}'."
        )
    if any(kw in keywords for kw in ["prince2", "pmp", "project management"]):
        return (
            f"{dept} requires project management capability. TKA offers "
            f"accredited PRINCE2/PMP certification with 98% pass rates, "
            f"deliverable on-site or virtually for cohorts of 5-15."
        )
    if "agile" in keywords or "scrum" in keywords:
        return (
            f"{dept} is adopting Agile practices. TKA provides AgilePM "
            f"and Scrum Master certification to accelerate their "
            f"transformation roadmap."
        )
    return (
        f"{dept} has a professional development need ('{title}'). "
        f"TKA can provide accredited training solutions tailored to "
        f"Government of Canada standards."
    )


# ---------------------------------------------------------------------------
# Database insertion
# ---------------------------------------------------------------------------

def store_opportunities(conn: sqlite3.Connection, rows: list[dict]):
    """Insert scored opportunities into the database."""
    inserted = 0
    for row in rows:
        tender_id = (
            row.get("tender_id")
            or row.get("reference_number")
            or row.get("solicitation_number")
            or f"auto-{hash(str(row)):016x}"
        )
        dept = row.get("department", row.get("owner_org", ""))
        title = row.get("title", row.get("description", ""))
        try:
            conn.execute("""
                INSERT OR IGNORE INTO opportunities
                    (tender_id, title, department, description,
                     published_date, closing_date,
                     signal_type, matched_keywords, priority_dept,
                     revenue_score, projected_revenue,
                     recommended_solution, consultative_brief)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tender_id,
                title[:500],
                dept,
                str(row.get("description", ""))[:2000],
                row.get("date_published", row.get("published_date", "")),
                row.get("date_closing", row.get("closing_date", "")),
                "Tender Opportunity",
                ", ".join(row.get("_matched_keywords", [])),
                1 if row.get("_priority_dept") else 0,
                row.get("_score", 0),
                row.get("_projected_revenue", 0),
                row.get("_solution", ""),
                row.get("_brief", ""),
            ))
            inserted += 1
        except sqlite3.Error as e:
            print(f"[!] DB insert error: {e}")
    conn.commit()
    print(f"[*] Stored {inserted} opportunities in database")


# ---------------------------------------------------------------------------
# Excel report generation
# ---------------------------------------------------------------------------

def generate_excel_report(conn: sqlite3.Connection, output_path: str):
    """Generate the pipeline Excel report for leads scoring >= 7."""
    try:
        import pandas as pd
    except ImportError:
        print("[!] pandas not installed. Run: pip install pandas openpyxl")
        return

    df = pd.read_sql_query("""
        SELECT
            department          AS "Department",
            signal_type         AS "Signal Source",
            branch              AS "Verified Branch",
            title               AS "Opportunity Title",
            matched_keywords    AS "Matched Keywords",
            recommended_solution AS "Recommended Solution",
            projected_revenue   AS "Projected Revenue (CAD)",
            revenue_score       AS "Score (1-10)",
            consultative_brief  AS "Consultative Brief",
            closing_date        AS "Closing Date",
            tender_id           AS "Reference",
            status              AS "Status"
        FROM opportunities
        WHERE revenue_score >= 7
        ORDER BY revenue_score DESC, projected_revenue DESC
    """, conn)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False, sheet_name="Pipeline", engine="openpyxl")
    total_pipeline = df["Projected Revenue (CAD)"].sum()
    print(f"[*] Report saved: {output_path}")
    print(f"    -> {len(df)} qualified leads (score >= 7)")
    print(f"    -> Total projected pipeline: ${total_pipeline:,.0f} CAD")
    return df


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run():
    """Execute the full opportunity monitoring pipeline."""
    print("=" * 60)
    print("  TKA Pipeline Monitor — CanadaBuys Open Data Analysis")
    print("=" * 60)
    print()

    conn = init_db()

    # Try downloading from CanadaBuys Open Data
    rows = download_csv(CANADABUYS_TENDER_CSV)

    # Fallback to local CSV if download fails
    if not rows:
        local_path = DB_PATH.parent / "tender_notices.csv"
        print(f"[*] Trying local CSV: {local_path}")
        rows = load_local_csv(str(local_path))

    if not rows:
        print()
        print("[!] No data available. To use this tool:")
        print("    1. Visit https://buyandsell.gc.ca/procurement-data")
        print("    2. Download the tender notices CSV")
        print("    3. Save it to: data/tender_notices.csv")
        print("    4. Re-run this script")
        print()
        # Still generate empty report structure
        generate_excel_report(
            conn,
            str(Path(__file__).resolve().parent.parent / "reports" / "march_revenue_hunt.xlsx"),
        )
        conn.close()
        return

    # Filter & score
    filtered = filter_opportunities(rows)
    scored = [score_opportunity(r) for r in filtered]

    # Generate briefs
    for row in scored:
        row["_brief"] = generate_consultative_brief(row)

    # Store in database
    store_opportunities(conn, scored)

    # Generate report
    report_path = str(
        Path(__file__).resolve().parent.parent / "reports" / "march_revenue_hunt.xlsx"
    )
    generate_excel_report(conn, report_path)

    conn.close()
    print()
    print("[✓] Pipeline monitor complete.")


if __name__ == "__main__":
    run()
