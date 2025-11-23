#!/usr/bin/env python3
"""
Generate a comprehensive report showing data collected from all accounts and platforms.
"""
import sys
import os
from datetime import date, datetime
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.schema import init_db, DimAccount, FactFollowersSnapshot
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, distinct

def generate_report(db_path='social_media.db'):
    """Generate comprehensive data collection report."""
    
    print("=" * 80)
    print("HHS SOCIAL MEDIA SCRAPER - DATA COLLECTION REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize database connection
    try:
        engine = init_db(db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
    except Exception as e:
        print(f"ERROR: Cannot connect to database: {e}")
        return
    
    try:
        # 1. Account Summary
        print("1. ACCOUNT SUMMARY")
        print("-" * 80)
        total_accounts = session.query(DimAccount).count()
        print(f"Total Accounts: {total_accounts}")
        
        # Accounts by platform
        platform_counts = session.query(
            DimAccount.platform,
            func.count(DimAccount.account_key).label('count')
        ).group_by(DimAccount.platform).all()
        
        print("\nAccounts by Platform:")
        for platform, count in sorted(platform_counts, key=lambda x: x[1], reverse=True):
            print(f"  {platform:20s}: {count:4d} accounts")
        
        # Accounts by organization
        org_counts = session.query(
            DimAccount.organization,
            func.count(DimAccount.account_key).label('count')
        ).group_by(DimAccount.organization).all()
        
        print(f"\nAccounts by Organization: {len(org_counts)} organizations")
        top_orgs = sorted(org_counts, key=lambda x: x[1], reverse=True)[:10]
        for org, count in top_orgs:
            print(f"  {org[:50]:50s}: {count:4d} accounts")
        if len(org_counts) > 10:
            print(f"  ... and {len(org_counts) - 10} more organizations")
        
        print()
        
        # 2. Data Collection Summary
        print("2. DATA COLLECTION SUMMARY")
        print("-" * 80)
        
        # Latest snapshot date
        latest_date = session.query(
            func.max(FactFollowersSnapshot.snapshot_date)
        ).scalar()
        
        if latest_date:
            print(f"Latest Snapshot Date: {latest_date}")
            
            # Snapshots by date
            snapshot_counts = session.query(
                FactFollowersSnapshot.snapshot_date,
                func.count(FactFollowersSnapshot.snapshot_key).label('count')
            ).group_by(FactFollowersSnapshot.snapshot_date).order_by(
                FactFollowersSnapshot.snapshot_date.desc()
            ).limit(10).all()
            
            print("\nRecent Snapshots:")
            for snap_date, count in snapshot_counts:
                print(f"  {snap_date}: {count:4d} snapshots")
        else:
            print("No snapshots found in database")
        
        print()
        
        # 3. Platform Coverage
        print("3. PLATFORM COVERAGE")
        print("-" * 80)
        
        if latest_date:
            # Accounts with data for latest date
            accounts_with_data = session.query(
                DimAccount.platform,
                func.count(distinct(FactFollowersSnapshot.account_key)).label('count')
            ).join(
                FactFollowersSnapshot,
                DimAccount.account_key == FactFollowersSnapshot.account_key
            ).filter(
                FactFollowersSnapshot.snapshot_date == latest_date
            ).group_by(DimAccount.platform).all()
            
            platform_data_map = {platform: count for platform, count in accounts_with_data}
            
            print("Accounts with Data (Latest Snapshot):")
            for platform, count in sorted(platform_data_map.items()):
                total_for_platform = next((c for p, c in platform_counts if p == platform), 0)
                percentage = (count / total_for_platform * 100) if total_for_platform > 0 else 0
                status = "✓" if count == total_for_platform else "⚠" if count > 0 else "✗"
                print(f"  {status} {platform:20s}: {count:4d}/{total_for_platform:4d} ({percentage:5.1f}%)")
            
            # Missing accounts
            print("\nMissing Data Analysis:")
            all_platforms = {p for p, _ in platform_counts}
            for platform in sorted(all_platforms):
                total = next((c for p, c in platform_counts if p == platform), 0)
                with_data = platform_data_map.get(platform, 0)
                missing = total - with_data
                
                if missing > 0:
                    print(f"\n  {platform} - {missing} accounts missing data:")
                    # Get accounts without data
                    accounts_without = session.query(DimAccount).filter(
                        DimAccount.platform == platform
                    ).filter(
                        ~DimAccount.account_key.in_(
                            session.query(FactFollowersSnapshot.account_key).filter(
                                FactFollowersSnapshot.snapshot_date == latest_date
                            )
                        )
                    ).limit(10).all()
                    
                    for account in accounts_without:
                        print(f"    - {account.organization[:40]:40s} ({account.handle})")
                    if missing > 10:
                        print(f"    ... and {missing - 10} more")
        else:
            print("No data collected yet - run the scraper first")
        
        print()
        
        # 4. Data Quality Metrics
        print("4. DATA QUALITY METRICS")
        print("-" * 80)
        
        if latest_date:
            # Metrics summary
            metrics = session.query(
                func.avg(FactFollowersSnapshot.followers_count).label('avg_followers'),
                func.max(FactFollowersSnapshot.followers_count).label('max_followers'),
                func.min(FactFollowersSnapshot.followers_count).label('min_followers'),
                func.sum(FactFollowersSnapshot.followers_count).label('total_followers'),
                func.avg(FactFollowersSnapshot.engagements_total).label('avg_engagement'),
                func.count(FactFollowersSnapshot.snapshot_key).label('total_snapshots')
            ).filter(
                FactFollowersSnapshot.snapshot_date == latest_date
            ).first()
            
            if metrics and metrics.total_snapshots:
                print(f"Total Snapshots: {metrics.total_snapshots}")
                print(f"Total Followers (All Platforms): {metrics.total_followers:,.0f}")
                print(f"Average Followers per Account: {metrics.avg_followers:,.0f}")
                print(f"Max Followers: {metrics.max_followers:,.0f}")
                print(f"Min Followers: {metrics.min_followers:,.0f}")
                if metrics.avg_engagement:
                    print(f"Average Engagement: {metrics.avg_engagement:,.0f}")
        
        print()
        
        # 5. Platform-Specific Metrics
        print("5. PLATFORM-SPECIFIC METRICS")
        print("-" * 80)
        
        if latest_date:
            platform_metrics = session.query(
                DimAccount.platform,
                func.count(FactFollowersSnapshot.snapshot_key).label('snapshots'),
                func.sum(FactFollowersSnapshot.followers_count).label('total_followers'),
                func.avg(FactFollowersSnapshot.followers_count).label('avg_followers'),
                func.max(FactFollowersSnapshot.followers_count).label('max_followers')
            ).join(
                FactFollowersSnapshot,
                DimAccount.account_key == FactFollowersSnapshot.account_key
            ).filter(
                FactFollowersSnapshot.snapshot_date == latest_date
            ).group_by(DimAccount.platform).all()
            
            print(f"{'Platform':<20} {'Snapshots':<12} {'Total Followers':<18} {'Avg Followers':<15} {'Max Followers':<15}")
            print("-" * 80)
            
            for platform, snapshots, total_fol, avg_fol, max_fol in sorted(platform_metrics, key=lambda x: x[2] or 0, reverse=True):
                total_fol = total_fol or 0
                avg_fol = avg_fol or 0
                max_fol = max_fol or 0
                print(f"{platform:<20} {snapshots:<12} {total_fol:>15,.0f} {avg_fol:>13,.0f} {max_fol:>13,.0f}")
        
        print()
        
        # 6. Recommendations
        print("6. RECOMMENDATIONS")
        print("-" * 80)
        
        if not latest_date:
            print("  ⚠ No data collected yet. Run the scraper to collect metrics.")
        else:
            # Check for missing data
            missing_count = 0
            for platform, total in platform_counts:
                with_data = platform_data_map.get(platform, 0)
                missing = total - with_data
                if missing > 0:
                    missing_count += missing
            
            if missing_count > 0:
                print(f"  ⚠ {missing_count} accounts are missing data. Consider re-running the scraper.")
            else:
                print("  ✓ All accounts have data collected!")
            
            # Check data freshness
            days_old = (date.today() - latest_date).days
            if days_old > 1:
                print(f"  ⚠ Data is {days_old} days old. Consider running a fresh scrape.")
            else:
                print("  ✓ Data is fresh!")
        
        print()
        print("=" * 80)
        print("Report Complete")
        print("=" * 80)
        
    except Exception as e:
        print(f"ERROR generating report: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'social_media.db'
    generate_report(db_path)

