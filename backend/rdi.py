from load_and_map_data import load_and_prepare_data
from predictive_analytics import count_recent_reactive_work

df = load_and_prepare_data()

# Check why high_failure_assets didn't trigger
print("Assets with 5+ failures in 90 days:")
assets = df['asset_id'].dropna().unique()
for asset in assets[:10]:  # Check first 10
    count = count_recent_reactive_work(df, asset, days=90)
    if count >= 5:
        print(f"  {asset}: {count} failures")

# Check technician counts
print("\nTechnician workload:")
print(df['technician'].value_counts().head())

# Check reactive work
reactive = df[df['type'].str.lower().str.contains('reactive', na=False)]
print(f"\nTotal reactive work orders: {len(reactive)}")