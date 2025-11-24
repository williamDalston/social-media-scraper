import json
import re
import logging
import sys
import os
from urllib.parse import urlparse
from sqlalchemy.orm import sessionmaker
from scraper.schema import DimAccount, init_db

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.logging_config import setup_logging, get_logger

# Set up logging if not already configured
try:
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        setup_logging()
    logger = get_logger(__name__)
except:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

def extract_handle(url, platform):
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    
    # Normalize platform name for comparison
    platform_lower = platform.lower()
    
    if platform_lower == 'x' or platform_lower == 'twitter':
        return path.split('/')[-1] # x.com/Handle
    elif platform_lower == 'facebook' or 'facebook' in platform_lower:
        if 'profile.php' in path:
            return path # Keep ID if it's a profile ID
        return path.split('/')[-1]
    elif platform_lower == 'instagram':
        return path.split('/')[0]
    elif platform_lower == 'linkedin':
        # linkedin.com/company/name or linkedin.com/showcase/name
        parts = path.split('/')
        if len(parts) > 1:
            return parts[1]
        return parts[0]
    elif platform_lower == 'youtube':
        # youtube.com/user/name or youtube.com/c/name or youtube.com/@handle
        parts = path.split('/')
        if len(parts) > 1 and parts[0] in ['user', 'c']:
            return parts[1]
        return path
    elif platform_lower == 'truth social' or platform_lower == 'truth_social':
        return path.replace('@', '')
    elif platform_lower == 'flickr':
        # flickr.com/photos/username or flickr.com/people/username
        parts = path.split('/')
        if len(parts) > 1:
            return parts[1]
        return parts[0]
    
    return path

def populate_accounts(json_path='hhs_accounts.json', db_path='social_media.db'):
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()

    with open(json_path, 'r') as f:
        accounts_data = json.load(f)

    count = 0
    for item in accounts_data:
        platform = item['platform']
        url = item['url']
        org_name = item['organization']
        
        handle = extract_handle(url, platform)
        
        # Check if account exists
        existing = session.query(DimAccount).filter_by(platform=platform, handle=handle).first()
        
        if not existing:
            account = DimAccount(
                platform=platform,
                handle=handle,
                account_url=url,
                org_name=org_name,
                account_display_name=f"{org_name} on {platform}",
                is_core_account=True if org_name == 'HHS' else False
            )
            session.add(account)
            count += 1
    
    session.commit()
    logger.info(
        "Successfully populated accounts",
        extra={
            'accounts_added': count,
            'json_path': json_path,
            'db_path': db_path
        }
    )
    session.close()

if __name__ == "__main__":
    populate_accounts()
