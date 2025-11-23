import argparse
from extract_accounts import populate_accounts
from collect_metrics import simulate_metrics
from schema import init_db
import logging
import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.logging_config import setup_logging, get_logger

# Set up logging
setup_logging()
logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description="HHS Social Media Scraper System")
    parser.add_argument('--init-db', action='store_true', help='Initialize the database')
    parser.add_argument('--extract-accounts', action='store_true', help='Extract and populate accounts from JSON')
    parser.add_argument('--collect-daily', action='store_true', help='Collect (simulate) daily metrics')
    parser.add_argument('--all', action='store_true', help='Run all steps')
    
    args = parser.parse_args()
    
    if args.init_db or args.all:
        logger.info("Initializing database...")
        init_db()
        
    if args.extract_accounts or args.all:
        logger.info("Populating accounts...")
        populate_accounts()
        
    if args.collect_daily or args.all:
        logger.info("Collecting daily metrics...")
        simulate_metrics()

if __name__ == "__main__":
    main()
