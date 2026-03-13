"""Generate the Excel pipeline report from the SQLite database."""

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tka_pipeline.sqlite"
REPORT_PATH = Path(__file__).resolve().parent.parent / "reports" / "march_revenue_hunt.xlsx"


def generate():
    conn = sqlite3.connect(str(DB_PATH))

    df = pd.read_sql_query("""
        SELECT
            department              AS "Department",
            signal_type             AS "Signal Source",
            branch                  AS "Verified Branch",
            title                   AS "Opportunity Title",
            matched_keywords        AS "Matched Keywords",
            recommended_solution    AS "Recommended Solution",
            projected_revenue       AS "Projected Revenue (CAD)",
            revenue_score           AS "Score (1-10)",
            consultative_brief      AS "Consultative Brief",
            closing_date            AS "Closing Date",
            tender_id               AS "Reference",
            status                  AS "Status"
        FROM opportunities
        WHERE revenue_score >= 7
        ORDER BY revenue_score DESC, projected_revenue DESC
    """, conn)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(str(REPORT_PATH), index=False, sheet_name="Pipeline", engine="openpyxl")

    total = df["Projected Revenue (CAD)"].sum()
    print(f"[*] Report: {REPORT_PATH}")
    print(f"    -> {len(df)} qualified leads (score >= 7)")
    print(f"    -> Total projected pipeline: ${total:,.0f} CAD")
    print()
    print(df[["Department", "Signal Source", "Score (1-10)", "Projected Revenue (CAD)"]].to_string(index=False))

    conn.close()


if __name__ == "__main__":
    generate()
