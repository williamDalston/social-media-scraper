#!/usr/bin/env python3
"""Export all data to JSON for static hosting."""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.schema import init_db, DimAccount, FactFollowersSnapshot
from sqlalchemy.orm import sessionmaker

def export_to_json(db_path='social_media.db', output_file='hhs_social_media_data.json'):
    """Export all data to JSON."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        query = session.query(
            DimAccount, FactFollowersSnapshot
        ).join(
            FactFollowersSnapshot,
            DimAccount.account_key == FactFollowersSnapshot.account_key
        ).order_by(
            FactFollowersSnapshot.snapshot_date.desc()
        ).all()
        
        data = []
        for account, snapshot in query:
            data.append({
                'platform': account.platform,
                'handle': account.handle,
                'organization': account.org_name,
                'account_url': account.account_url,
                'snapshot_date': snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else None,
                'followers_count': snapshot.followers_count,
                'following_count': snapshot.following_count,
                'posts_count': snapshot.posts_count,
                'engagements_total': snapshot.engagements_total,
                'likes_count': snapshot.likes_count,
                'comments_count': snapshot.comments_count,
                'shares_count': snapshot.shares_count,
            })
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'total_records': len(data),
            'data': data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported {len(data)} records to {output_file}")
        return len(data)
        
    finally:
        session.close()

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'social_media.db'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'hhs_social_media_data.json'
    export_to_json(db_path, output_file)

