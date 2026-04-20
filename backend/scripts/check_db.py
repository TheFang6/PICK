"""Check database connection and print status."""
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

url = os.getenv("DATABASE_URL")
if not url:
    print("❌ DATABASE_URL not set in .env")
    sys.exit(1)

try:
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
        print(f"✅ Connected!\n   {version}")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)
