"""
Database Seeding Strategies.

Utilities for seeding test databases with realistic data.
"""
from datetime import date, timedelta
import random
from scraper.schema import DimAccount, FactFollowersSnapshot


def seed_basic_data(session, num_accounts=10, days_of_history=30):
    """Seed database with basic test data."""
    accounts = []
    platforms = ['X', 'Instagram', 'Facebook', 'YouTube', 'LinkedIn']
    orgs = ['HHS', 'NIH', 'CDC', 'FDA', 'CMS']
    
    for i in range(num_accounts):
        platform = random.choice(platforms)
        org = random.choice(orgs)
        handle = f"{org.lower()}_{platform.lower()}_{i}"
        
        account = DimAccount(
            platform=platform,
            handle=handle,
            org_name=org,
            account_display_name=f"{org} on {platform}",
            account_url=f"https://{platform.lower()}.com/{handle}",
            is_core_account=(org == 'HHS')
        )
        session.add(account)
        accounts.append(account)
    
    session.commit()
    
    # Create historical snapshots
    today = date.today()
    for account in accounts:
        base_followers = 500000 if account.org_name == 'HHS' else 100000
        
        for day_offset in range(days_of_history):
            snapshot_date = today - timedelta(days=days_of_history - day_offset - 1)
            
            # Simulate growth
            growth_factor = 1 + (day_offset * 0.001)  # 0.1% daily growth
            followers = int(base_followers * growth_factor) + random.randint(-1000, 1000)
            
            snapshot = FactFollowersSnapshot(
                account_key=account.account_key,
                snapshot_date=snapshot_date,
                followers_count=max(1000, followers),
                following_count=random.randint(10, 500),
                posts_count=random.randint(0, 5),
                likes_count=random.randint(50, 5000),
                comments_count=random.randint(5, 500),
                shares_count=random.randint(10, 1000),
                engagements_total=0
            )
            snapshot.engagements_total = (
                snapshot.likes_count + snapshot.comments_count + snapshot.shares_count
            )
            session.add(snapshot)
    
    session.commit()
    return accounts


def seed_large_dataset(session, num_accounts=100, days_of_history=365):
    """Seed database with large dataset for performance testing."""
    return seed_basic_data(session, num_accounts, days_of_history)


def seed_minimal_data(session):
    """Seed database with minimal data for quick tests."""
    account = DimAccount(
        platform='X',
        handle='test',
        org_name='HHS',
        account_display_name='HHS on X',
        account_url='https://x.com/test',
        is_core_account=True
    )
    session.add(account)
    session.commit()
    
    snapshot = FactFollowersSnapshot(
        account_key=account.account_key,
        snapshot_date=date.today(),
        followers_count=1000,
        engagements_total=500
    )
    session.add(snapshot)
    session.commit()
    
    return account


def seed_edge_case_data(session):
    """Seed database with edge case data."""
    accounts = []
    
    # Account with very long handle
    account1 = DimAccount(
        platform='X',
        handle='a' * 100,  # Very long handle
        org_name='HHS',
        account_url='https://x.com/' + 'a' * 100
    )
    session.add(account1)
    accounts.append(account1)
    
    # Account with special characters
    account2 = DimAccount(
        platform='X',
        handle='test_handle-123',
        org_name='HHS',
        account_url='https://x.com/test_handle-123'
    )
    session.add(account2)
    accounts.append(account2)
    
    # Account with zero followers
    account3 = DimAccount(
        platform='X',
        handle='zero_followers',
        org_name='HHS',
        account_url='https://x.com/zero_followers'
    )
    session.add(account3)
    accounts.append(account3)
    
    session.commit()
    
    # Create snapshots with edge cases
    snapshot1 = FactFollowersSnapshot(
        account_key=account3.account_key,
        snapshot_date=date.today(),
        followers_count=0,
        engagements_total=0
    )
    session.add(snapshot1)
    
    # Snapshot with very large numbers
    snapshot2 = FactFollowersSnapshot(
        account_key=account1.account_key,
        snapshot_date=date.today(),
        followers_count=999999999,
        engagements_total=99999999
    )
    session.add(snapshot2)
    
    session.commit()
    return accounts

