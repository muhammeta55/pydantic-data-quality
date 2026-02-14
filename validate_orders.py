import pandas as pd
from pydantic import BaseModel, Field, field_validator, ValidationError
from datetime import datetime
import requests
import json
import os

# Get webhook from environment variable (will be set by GitHub Actions)
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')


def send_slack_notification(invalid_count, total_count):
    """Send Slack alert when validation fails"""
    
    message = {
        "text": f"⚠️ *Amazon Orders Validation Alert*\n\n"
                f"• Total rows: {total_count}\n"
                f"• Valid rows: {total_count - invalid_count}\n"
                f"• Invalid rows: {invalid_count}\n\n"
                f"❌ Please check `invalid_rows.csv` for details."
    }
    
    # If no webhook URL, just print the message
    if not SLACK_WEBHOOK_URL:
        print("\n" + "="*50)
        print("📢 SLACK NOTIFICATION (Mock - No Webhook Configured)")
        print("="*50)
        print(message['text'])
        print("="*50)
        return
    
    # Send to Slack
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(message),
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            print("\n✅ Slack notification sent successfully!")
        else:
            print(f"\n❌ Slack notification failed: {response.status_code}")
            
    except Exception as e:
        print(f"\n❌ Error sending Slack notification: {e}")


class AmazonOrder(BaseModel):
    order_id: str = Field(min_length=1)
    qty: int = Field(ge=0)
    amount: float = Field(ge=0)
    currency: str
    ship_country: str
    date: str
    
    @field_validator('currency')
    @classmethod
    def check_currency(cls, value):
        if value != "INR":
            raise ValueError("Currency must be INR")
        return value
    
    @field_validator('ship_country')
    @classmethod
    def check_country(cls, value):
        if value != "IN":
            raise ValueError("Ship country must be IN")
        return value
    
    @field_validator('date')
    @classmethod
    def check_date_format(cls, value):
        try:
            datetime.strptime(value, "%m-%d-%y")
        except ValueError:
            raise ValueError("Date must be in format MM-DD-YY")
        return value

# Load CSV
print("="*50)
print("📂 Loading CSV File")
print("="*50)
df = pd.read_csv('amazon_orders.csv')
print(f"✅ Loaded {len(df)} rows\n")

# Prepare lists
valid_rows = []
invalid_rows = []

# Validate each row
print("="*50)
print("🔍 Validating Rows")
print("="*50)

for index, row in df.iterrows():
    row_number = index + 1
    
    try:
        row_dict = row.to_dict()
        order = AmazonOrder(**row_dict)
        valid_rows.append(row_dict)
        print(f"✅ Row {row_number}: Valid - {row_dict['order_id']}")
        
    except ValidationError as e:
        row_dict = row.to_dict()
        row_dict['validation_errors'] = str(e.error_count()) + " error(s)"
        invalid_rows.append(row_dict)
        
        print(f"❌ Row {row_number}: Invalid")
        for error in e.errors():
            field = error['loc'][0]
            message = error['msg']
            print(f"   • {field}: {message}")

# Summary
print("\n" + "="*50)
print("📊 Validation Summary")
print("="*50)
print(f"Total rows:   {len(df)}")
print(f"Valid rows:   {len(valid_rows)}")
print(f"Invalid rows: {len(invalid_rows)}")
print("="*50)

# Save to CSV files
print("\n" + "="*50)
print("💾 Saving Results")
print("="*50)

if len(valid_rows) > 0:
    valid_df = pd.DataFrame(valid_rows)
    valid_df.to_csv('valid_rows.csv', index=False)
    print(f"✅ Saved {len(valid_rows)} valid rows to 'valid_rows.csv'")
else:
    print("⚠️  No valid rows to save")

if len(invalid_rows) > 0:
    invalid_df = pd.DataFrame(invalid_rows)
    invalid_df.to_csv('invalid_rows.csv', index=False)
    print(f"❌ Saved {len(invalid_rows)} invalid rows to 'invalid_rows.csv'")
else:
    print("✅ No invalid rows found")

print("="*50)

# Send Slack notification if there are invalid rows
if len(invalid_rows) > 0:
    send_slack_notification(len(invalid_rows), len(df))

import sys

# ... (keep all your existing code) ...

# Add this at the very end (after Slack notification):
print("\n" + "="*50)
if len(invalid_rows) > 0:
    print(f"❌ VALIDATION FAILED")
    print(f"   Invalid rows: {len(invalid_rows)}")
    print(f"   Check invalid_rows.csv for details")
    print("="*50)
    sys.exit(1)  # Exit with error code - CI will fail
else:
    print(f"✅ VALIDATION PASSED")
    print(f"   All {len(valid_rows)} rows are valid")
    print("="*50)
    sys.exit(0)  # Exit successfully - CI will pass


