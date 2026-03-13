"""
Seed the pipeline database with publicly known tender examples
so the scoring/reporting pipeline can be validated end-to-end.

These are based on publicly documented Government of Canada procurement
categories and departmental mandates — not scraped personal data.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tka_pipeline.sqlite"


SAMPLE_OPPORTUNITIES = [
    {
        "tender_id": "EN578-240001",
        "title": "Professional Development Training Services — Project Management (PRINCE2/PMP)",
        "department": "Shared Services Canada",
        "branch": "Chief Information Officer Branch",
        "description": "Requirement for accredited project management training for IT professionals including PRINCE2 Practitioner and PMP certification preparation courses.",
        "published_date": "2026-02-15",
        "closing_date": "2026-04-01",
        "signal_type": "Tender Opportunity",
        "matched_keywords": "prince2, pmp, project management, training",
        "priority_dept": 1,
        "revenue_score": 10,
        "projected_revenue": 35000,
        "recommended_solution": "Full certification program (PRINCE2 + PMP cohort, 15 seats)",
        "consultative_brief": "SSC is investing in PM capability for its IT workforce. TKA can deliver accredited PRINCE2/PMP certification with 98% pass rates for a cohort of 15, on-site at SSC Ottawa or virtually.",
    },
    {
        "tender_id": "W8486-260012",
        "title": "Cyber Security Certification Training — CISSP and CISM",
        "department": "Department of National Defence",
        "branch": "Director General Information Management",
        "description": "Training services for cyber security professionals requiring CISSP and CISM certifications aligned with the 2026 Cyber Resilience Framework.",
        "published_date": "2026-03-01",
        "closing_date": "2026-04-15",
        "signal_type": "Tender Opportunity",
        "matched_keywords": "cyber security, cissp, cism, training, certification",
        "priority_dept": 1,
        "revenue_score": 10,
        "projected_revenue": 50000,
        "recommended_solution": "CISSP + CISM dual certification program (10-day intensive, 20 seats)",
        "consultative_brief": "DND is implementing the 2026 Cyber Resilience Framework. TKA can deliver CISSP/CISM certification for their security team in a 10-day intensive, meeting their April deadline.",
    },
    {
        "tender_id": "47419-260003",
        "title": "ITIL 4 Foundation and Practitioner Training",
        "department": "Canada Border Services Agency",
        "branch": "Information, Science and Technology Branch",
        "description": "ITIL 4 certification training for IT service management professionals supporting digital transformation initiatives.",
        "published_date": "2026-02-20",
        "closing_date": "2026-03-30",
        "signal_type": "Tender Opportunity",
        "matched_keywords": "itil, training, certification, digital transformation",
        "priority_dept": 1,
        "revenue_score": 9,
        "projected_revenue": 25000,
        "recommended_solution": "ITIL 4 Foundation + Practitioner (5-day program, 15 seats)",
        "consultative_brief": "CBSA is undergoing digital transformation of border services. TKA provides ITIL 4 certification aligned to GC IT service management standards.",
    },
    {
        "tender_id": "HIRING-TBS-2026-PM",
        "title": "Hiring Signal: Treasury Board hiring 8 Project Managers",
        "department": "Treasury Board of Canada Secretariat",
        "branch": "Office of the Chief Information Officer",
        "description": "TBS OCIO is actively recruiting 8 IT Project Managers (IT-03/IT-04). Job postings do not list PRINCE2 or PMP as requirements — indicating a training gap for incoming staff.",
        "published_date": "2026-03-10",
        "closing_date": "",
        "signal_type": "Hiring Surge",
        "matched_keywords": "project management, training, digital transformation",
        "priority_dept": 1,
        "revenue_score": 8,
        "projected_revenue": 20000,
        "recommended_solution": "Group PRINCE2 certification for new PM cohort (8 seats, 5-day intensive)",
        "consultative_brief": "TBS OCIO is scaling its PMO with 8 new hires. TKA can certify the entire incoming cohort in PRINCE2 within their first month — reducing ramp-up time.",
    },
    {
        "tender_id": "HIRING-ESDC-2026-IT",
        "title": "Hiring Signal: ESDC hiring 12 IT Analysts for Benefits Delivery Modernization",
        "department": "Employment and Social Development Canada",
        "branch": "Innovation, Information and Technology Branch",
        "description": "ESDC IITB is recruiting 12 IT Analysts for the Benefits Delivery Modernization programme. Agile and digital transformation skills are needed.",
        "published_date": "2026-03-05",
        "closing_date": "",
        "signal_type": "Hiring Surge",
        "matched_keywords": "agile, digital transformation, modernization, training",
        "priority_dept": 1,
        "revenue_score": 8,
        "projected_revenue": 20000,
        "recommended_solution": "AgilePM + Scrum Master certification (12 seats across 2 cohorts)",
        "consultative_brief": "ESDC is scaling up for Benefits Delivery Modernization. TKA can deliver AgilePM certification for new analysts to ensure day-one Agile capability.",
    },
    {
        "tender_id": "MANDATE-HC-2026-CYBER",
        "title": "Mandate Change: Health Canada implementing new Cyber Security Framework",
        "department": "Health Canada",
        "branch": "Chief Information Officer Branch",
        "description": "Health Canada is adopting the updated GC Cyber Security Event Management Plan. Staff require CISSP/CISM certifications to meet compliance requirements.",
        "published_date": "2026-03-01",
        "closing_date": "",
        "signal_type": "Mandate Change",
        "matched_keywords": "cyber security, cissp, cism, certification",
        "priority_dept": 0,
        "revenue_score": 8,
        "projected_revenue": 15000,
        "recommended_solution": "CISSP certification fast-track (5 seats, 5-day bootcamp)",
        "consultative_brief": "With Health Canada adopting the new GC Cyber Security framework, their team needs CISSP/CISM fast. TKA delivers a 5-day bootcamp with 98% pass rate.",
    },
    {
        "tender_id": "HIRING-IRCC-2026-PM",
        "title": "Hiring Signal: IRCC hiring 6 Project Managers for digital intake modernization",
        "department": "Immigration, Refugees and Citizenship Canada",
        "branch": "Digital Services Branch",
        "description": "IRCC is hiring 6 PMs for its digital intake platform modernization. Postings mention Agile experience preferred but no formal certification requirement.",
        "published_date": "2026-03-08",
        "closing_date": "",
        "signal_type": "Hiring Surge",
        "matched_keywords": "project management, agile, modernization, training",
        "priority_dept": 1,
        "revenue_score": 8,
        "projected_revenue": 15000,
        "recommended_solution": "PRINCE2 Agile certification (6 seats, blended delivery)",
        "consultative_brief": "IRCC is modernizing digital intake with 6 new PMs. TKA's PRINCE2 Agile certification bridges the gap between their Agile preference and formal PM governance.",
    },
    {
        "tender_id": "EN578-260045",
        "title": "Professional Services — Agile Coaching and Scrum Training",
        "department": "Canada Revenue Agency",
        "branch": "Information Technology Branch",
        "description": "CRA requires Agile coaching services including Scrum Master and Product Owner certification training for IT teams transitioning to Agile delivery.",
        "published_date": "2026-02-28",
        "closing_date": "2026-04-10",
        "signal_type": "Tender Opportunity",
        "matched_keywords": "agile, scrum, training, professional services, certification",
        "priority_dept": 1,
        "revenue_score": 9,
        "projected_revenue": 30000,
        "recommended_solution": "Scrum Master + Product Owner certification program (20 seats, 2 cohorts)",
        "consultative_brief": "CRA is transitioning IT teams to Agile. TKA provides certified Scrum Master and Product Owner training that meets GC procurement standards.",
    },
]


def seed(db_path: Path = DB_PATH):
    """Insert sample opportunities into the database."""
    conn = sqlite3.connect(str(db_path))

    inserted = 0
    for opp in SAMPLE_OPPORTUNITIES:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO opportunities
                    (tender_id, title, department, branch, description,
                     published_date, closing_date,
                     signal_type, matched_keywords, priority_dept,
                     revenue_score, projected_revenue,
                     recommended_solution, consultative_brief)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                opp["tender_id"],
                opp["title"],
                opp["department"],
                opp["branch"],
                opp["description"],
                opp["published_date"],
                opp["closing_date"],
                opp["signal_type"],
                opp["matched_keywords"],
                opp["priority_dept"],
                opp["revenue_score"],
                opp["projected_revenue"],
                opp["recommended_solution"],
                opp["consultative_brief"],
            ))
            inserted += 1
        except Exception as e:
            print(f"[!] Error: {e}")

    conn.commit()
    conn.close()
    print(f"[*] Seeded {inserted} sample opportunities into {db_path}")


if __name__ == "__main__":
    seed()
