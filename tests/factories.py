"""
Test Data Factories.

Factories for creating test data with realistic values and relationships.
"""
import random
from datetime import date, timedelta
from factory import Factory, Faker, LazyAttribute, SubFactory
from factory.alchemy import SQLAlchemyModelFactory
from scraper.schema import DimAccount, FactFollowersSnapshot, FactSocialPost


class DimAccountFactory(SQLAlchemyModelFactory):
    """Factory for creating DimAccount instances."""
    
    class Meta:
        model = DimAccount
        sqlalchemy_session_persistence = 'commit'
    
    platform = Faker('random_element', elements=['X', 'Instagram', 'Facebook', 'YouTube', 'LinkedIn', 'Truth Social'])
    handle = Faker('user_name')
    org_name = Faker('random_element', elements=['HHS', 'NIH', 'CDC', 'FDA', 'CMS'])
    account_display_name = LazyAttribute(lambda obj: f"{obj.org_name} on {obj.platform}")
    account_url = LazyAttribute(lambda obj: f"https://{obj.platform.lower()}.com/{obj.handle}")
    is_core_account = LazyAttribute(lambda obj: obj.org_name == 'HHS')
    is_leader_account = False
    requires_preclearance = False
    sensitivity_level = Faker('random_element', elements=['Low', 'Medium', 'High', None])
    verified_status = Faker('random_element', elements=[None, 'Blue', 'Org', 'Gov'])


class FactFollowersSnapshotFactory(SQLAlchemyModelFactory):
    """Factory for creating FactFollowersSnapshot instances."""
    
    class Meta:
        model = FactFollowersSnapshot
        sqlalchemy_session_persistence = 'commit'
    
    account = SubFactory(DimAccountFactory)
    account_key = LazyAttribute(lambda obj: obj.account.account_key)
    snapshot_date = Faker('date_between', start_date='-1y', end_date='today')
    
    # Realistic follower counts based on platform and org
    followers_count = LazyAttribute(lambda obj: _get_follower_count(obj.account))
    following_count = Faker('random_int', min=10, max=500)
    posts_count = Faker('random_int', min=0, max=10)
    likes_count = LazyAttribute(lambda obj: random.randint(50, obj.followers_count // 10))
    comments_count = LazyAttribute(lambda obj: random.randint(5, obj.followers_count // 100))
    shares_count = LazyAttribute(lambda obj: random.randint(10, obj.followers_count // 50))
    engagements_total = LazyAttribute(
        lambda obj: (obj.likes_count or 0) + (obj.comments_count or 0) + (obj.shares_count or 0)
    )


class FactSocialPostFactory(SQLAlchemyModelFactory):
    """Factory for creating FactSocialPost instances."""
    
    class Meta:
        model = FactSocialPost
        sqlalchemy_session_persistence = 'commit'
    
    account = SubFactory(DimAccountFactory)
    account_key = LazyAttribute(lambda obj: obj.account.account_key)
    platform = LazyAttribute(lambda obj: obj.account.platform)
    post_id = Faker('uuid4')
    post_url = LazyAttribute(lambda obj: f"https://{obj.platform.lower()}.com/{obj.account.handle}/status/{obj.post_id}")
    post_datetime_utc = Faker('date_time_between', start_date='-30d', end_date='now')
    post_type = Faker('random_element', elements=['text', 'image', 'video', 'carousel'])
    caption_text = Faker('text', max_nb_chars=500)
    likes_count = Faker('random_int', min=0, max=10000)
    comments_count = Faker('random_int', min=0, max=1000)
    shares_count = Faker('random_int', min=0, max=5000)
    views_count = Faker('random_int', min=0, max=100000)
    is_reply = False
    is_retweet = False


def _get_follower_count(account):
    """Generate realistic follower count based on account properties."""
    base_followers = {
        'HHS': 500000,
        'NIH': 200000,
        'CDC': 300000,
        'FDA': 150000,
        'CMS': 100000,
    }
    
    base = base_followers.get(account.org_name, 10000)
    
    # Add some randomness
    variation = random.randint(-base // 10, base // 10)
    
    return max(1000, base + variation)


# Convenience functions for common test scenarios
def create_account_with_snapshots(session, num_snapshots=30, **account_kwargs):
    """Create an account with historical snapshots."""
    account = DimAccountFactory(**account_kwargs)
    session.add(account)
    session.flush()
    
    snapshots = []
    today = date.today()
    for i in range(num_snapshots):
        snapshot_date = today - timedelta(days=num_snapshots - i - 1)
        snapshot = FactFollowersSnapshotFactory(
            account=account,
            snapshot_date=snapshot_date
        )
        snapshots.append(snapshot)
    
    session.commit()
    return account, snapshots


def create_multiple_accounts(session, count=10, **kwargs):
    """Create multiple accounts."""
    accounts = []
    for _ in range(count):
        account = DimAccountFactory(**kwargs)
        accounts.append(account)
    
    session.commit()
    return accounts

