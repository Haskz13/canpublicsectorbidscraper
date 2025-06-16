# backend/tasks.py
from celery import Celery
from celery.schedules import crontab
import os
from datetime import datetime, timedelta
import logging
from typing import List, Dict
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
from pathlib import Path

# Import from main module
from main import (
    SessionLocal, 
    Tender, 
    ProcurementScanner, 
    PORTAL_CONFIGS,
    TenderMatcher,
    TKA_COURSES,
    save_tender_to_db,
    logger
)

# Import from scrapers module
from scrapers import (
    ProvincialScrapers,
    MunicipalScrapers,
    SpecializedScrapers,
    HealthEducationScrapers
)

# This dispatcher maps a portal_id to its corresponding scraper function.
SCRAPER_DISPATCHER = {
    # --- Functions from main.py (called via the scanner instance) ---
    'canadabuys': 'scan_canadabuys',
    'merx': 'scan_merx',
    'bcbid': 'scan_bcbid',
    'seao': 'scan_seao',
    'toronto': 'scan_ariba_portal',
    'biddingo': 'scan_biddingo',
    'london': 'scan_biddingo', # Uses the generic biddingo scraper
    'hamilton': 'scan_biddingo', # Uses the generic biddingo scraper
    'kitchener': 'scan_biddingo', # Uses the generic biddingo scraper

    # --- Functions from scrapers.py (called as static methods) ---
    
    # Provincial Portals
    'albertapurchasing': ProvincialScrapers.scan_alberta_purchasing,
    'sasktenders': ProvincialScrapers.scan_saskatchewan_tenders,
    'manitoba': ProvincialScrapers.scan_manitoba_tenders,
    'ontario': ProvincialScrapers.scan_ontario_tenders,
    'ns': ProvincialScrapers.scan_ns_tenders,
    
    # Municipal Portals
    'ottawa': MunicipalScrapers.scan_ottawa_bids,
    'edmonton': MunicipalScrapers.scan_edmonton_bids,
    'calgary': MunicipalScrapers.scan_calgary_procurement,
    'winnipeg': MunicipalScrapers.scan_winnipeg_bids,
    'vancouver': MunicipalScrapers.scan_vancouver_procurement,
    'halifax': MunicipalScrapers.scan_halifax_procurement,
    'regina': MunicipalScrapers.scan_regina_procurement,

    # Specialized Portals
    'nbon': SpecializedScrapers.scan_nbon_newbrunswick,
    'pei': SpecializedScrapers.scan_pei_tenders,
    'nl': SpecializedScrapers.scan_nl_procurement,

    # Health & Education Portals
    'buybc': HealthEducationScrapers.scan_buybc_health,
    'mohltc': HealthEducationScrapers.scan_ontario_health,

    # Portals that are aliases of others (handled by their primary scraper type)
    'montreal': 'seao', # Montreal uses SEAO
    'quebec_city': 'seao', # Quebec City uses SEAO
    'saskatoon': 'sasktenders' # Saskatoon uses SaskTenders
}

# Configure Celery
app = Celery(
    'procurement_scanner',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Toronto',
    enable_utc=True,
)

# Configure periodic tasks
app.conf.beat_schedule = {
    'scan-all-portals-hourly': {
        'task': 'tasks.scan_all_portals_task',
        'schedule': crontab(minute=0),
    },
    'scan-high-priority-frequent': {
        'task': 'tasks.scan_high_priority_portals',
        'schedule': crontab(minute='*/15'),
    },
    'scan-municipal-morning': {
        'task': 'tasks.scan_municipal_portals',
        'schedule': crontab(hour=7, minute=30),
    },
    'scan-provincial-afternoon': {
        'task': 'tasks.scan_provincial_portals',
        'schedule': crontab(hour=13, minute=30),
    },
    'clean-expired-tenders': {
        'task': 'tasks.clean_expired_tenders',
        'schedule': crontab(hour=2, minute=0),
    },
    'generate-daily-report': {
        'task': 'tasks.generate_daily_report',
        'schedule': crontab(hour=7, minute=0),
    },
    'generate-weekly-summary': {
        'task': 'tasks.generate_weekly_summary',
        'schedule': crontab(day_of_week=1, hour=8, minute=0),
    },
    'backup-database': {
        'task': 'tasks.backup_database',
        'schedule': crontab(hour=3, minute=0),
    },
    'analyze-tender-trends': {
        'task': 'tasks.analyze_tender_trends',
        'schedule': crontab(day_of_week=0, hour=9, minute=0),
    }
}


def _process_tenders(tenders: List[Dict], portal_name: str, results: Dict, matcher: TenderMatcher):
    """Process and save tenders to database using the helper function from main."""
    if not tenders:
        return

    db = SessionLocal()
    portal_results = results['by_portal'].get(portal_name, {'found': 0, 'new': 0, 'updated': 0})
    portal_results['found'] += len(tenders)
    
    try:
        for tender_data in tenders:
            tender_data['matching_courses'] = matcher.match_courses(tender_data)
            tender_data['priority'] = matcher.calculate_priority(tender_data)

            was_new = save_tender_to_db(db, tender_data)

            if was_new:
                portal_results['new'] += 1
                results['new_tenders'] += 1
            else:
                portal_results['updated'] += 1
                results['updated_tenders'] += 1

        results['total_found'] += len(tenders)
        results['by_portal'][portal_name] = portal_results
    except Exception as e:
        logger.error(f"Error processing tenders for {portal_name}: {e}")
    finally:
        db.close()


async def _execute_scans_async(scanner: ProcurementScanner, portal_ids: List[str], results: Dict, matcher: TenderMatcher):
    """
    The async helper that iterates through portals and calls the correct scraper function.
    """
    driver = None
    session = await scanner.get_session()
    
    for portal_id in portal_ids:
        if portal_id not in PORTAL_CONFIGS:
            logger.warning(f"Configuration for portal_id '{portal_id}' not found. Skipping.")
            continue

        config = PORTAL_CONFIGS[portal_id]
        scraper_func_ref = SCRAPER_DISPATCHER.get(portal_id)

        if isinstance(scraper_func_ref, str) and scraper_func_ref in SCRAPER_DISPATCHER:
            scraper_func_ref = SCRAPER_DISPATCHER.get(scraper_func_ref)
            
        if not callable(scraper_func_ref):
            logger.warning(f"No valid scraper function found for portal_id: {portal_id}")
            continue

        try:
            logger.info(f"Scanning portal: {config['name']}")
            tenders = []
            
            if config.get('requires_selenium', False):
                if driver is None:
                    driver = scanner.selenium.get_driver()
                
                # Check if the function is a method of the scanner instance
                if hasattr(scanner, scraper_func_ref.__name__):
                    method_to_call = getattr(scanner, scraper_func_ref.__name__)
                    # Handle methods that need extra arguments like scan_ariba_portal
                    if scraper_func_ref.__name__ in ['scan_ariba_portal', 'scan_biddingo']:
                         tenders = await method_to_call(config['name'], config)
                    else:
                        tenders = await method_to_call()
                else: # Static method from scrapers.py
                    tenders = await scraper_func_ref(driver, scanner.selenium)
            else: # Non-selenium static method
                tenders = await scraper_func_ref(session)
            
            if tenders:
                 _process_tenders(tenders, config['name'], results, matcher)
            results['scanned'].append(portal_id)

        except Exception as e:
            logger.error(f"Error scanning {config['name']}: {e}", exc_info=True)
            results['errors'].append({'portal': config['name'], 'error': str(e)})
        
    if driver:
        driver.quit()
    await scanner.close_session()


@app.task(bind=True, max_retries=3)
def scan_specific_portals_task(self, portal_ids: List[str]):
    """The new master task that scans a specific list of portals using the dispatcher."""
    scanner = ProcurementScanner()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    results = {'scanned': [], 'total_found': 0, 'new_tenders': 0, 'updated_tenders': 0, 'errors': [], 'by_portal': {}}
    matcher = TenderMatcher()
    
    try:
        loop.run_until_complete(
            _execute_scans_async(scanner, portal_ids, results, matcher)
        )
    except Exception as e:
        logger.error(f"Fatal error in scan_specific_portals task: {e}")
        self.retry(countdown=300)
    finally:
        loop.close()
        
    return results


@app.task
def scan_all_portals_task():
    """Scan all configured portals."""
    all_portal_ids = list(PORTAL_CONFIGS.keys())
    return scan_specific_portals_task.delay(all_portal_ids)


@app.task
def scan_high_priority_portals():
    """Scan only high-traffic portals more frequently."""
    high_priority_ids = ['canadabuys', 'merx', 'toronto', 'ontario', 'bcbid', 'seao']
    return scan_specific_portals_task.delay(high_priority_ids)


@app.task
def scan_municipal_portals():
    """Scan all municipal portals."""
    municipal_ids = [k for k,v in PORTAL_CONFIGS.items() if 'City of' in v['name'] or 'Municipality' in v['name']]
    return scan_specific_portals_task.delay(municipal_ids)


@app.task
def scan_provincial_portals():
    """Scan all provincial portals."""
    provincial_ids = [k for k,v in PORTAL_CONFIGS.items() if 'provincial' in v.get('category', '').lower()]
    # Fallback if category is not set
    if not provincial_ids:
        provincial_ids = ['bcbid', 'albertapurchasing', 'sasktenders', 'manitoba', 
                          'ontario', 'seao', 'nbon', 'ns', 'pei', 'nl']
    return scan_specific_portals_task.delay(provincial_ids)


@app.task
def clean_expired_tenders():
    """Mark expired tenders as inactive and clean old data."""
    db = SessionLocal()
    try:
        expired_count = db.query(Tender).filter(
            Tender.closing_date < datetime.utcnow(),
            Tender.is_active == True
        ).update({'is_active': False}, synchronize_session=False)
        
        old_date = datetime.utcnow() - timedelta(days=180)
        deleted_count = db.query(Tender).filter(
            Tender.closing_date < old_date,
            Tender.is_active == False
        ).delete(synchronize_session=False)
        
        db.commit()
        logger.info(f"Cleaned expired tenders. Deactivated: {expired_count}, Deleted old: {deleted_count}")
        return {'deactivated': expired_count, 'deleted': deleted_count}
    except Exception as e:
        logger.error(f"Error cleaning expired tenders: {e}")
        db.rollback()
    finally:
        db.close()


# Other maintenance tasks (stubs)
@app.task
def generate_daily_report():
    logger.info("Generating daily report... (Not Implemented)")
    return "Daily report generation is not implemented."

@app.task
def generate_weekly_summary():
    logger.info("Generating weekly summary... (Not Implemented)")
    return "Weekly summary generation is not implemented."

@app.task
def backup_database():
    logger.info("Backing up database... (Not Implemented)")
    return "Database backup is not implemented."

@app.task
def analyze_tender_trends():
    logger.info("Analyzing tender trends... (Not Implemented)")
    return "Trend analysis is not implemented."