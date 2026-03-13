# The Knowledge Academy: Lead Gen Architecture

## Business Context
- **Product:** Professional certifications (PRINCE2, ITIL, PMP, Cyber Security).
- **Target:** Canadian Public Sector (Federal, Provincial, Municipal) & Indigenous Orgs.
- **Value Prop:** Bridging the "Skills Gap" in digital transformation projects.

## Lead Definitions
- **High Intent:** Active RFP on CanadaBuys/MERX or hiring for roles *without* certifications.
- **Verification Rule:** All emails must be cross-referenced against the GEDS (Government Electronic Directory Service) or provincial directories.

## Technical Constraints
- Use **Agent Teams** for parallelizing regional searches.
- Store all leads in `data/master_leads.sqlite` to prevent duplicates.
- All browser actions must use a 2-second 'human-delay' to avoid IP blocks.
