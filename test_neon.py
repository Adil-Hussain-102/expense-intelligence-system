import os
from sqlalchemy import create_engine, text

PASSWORD = "npg_sA9UbkCrJ4mf"
HOST = "ep-wild-salad-an3s1bki-pooler.c-6.us-east-1.aws.neon.tech"

engine = create_engine(
    f"postgresql://neondb_owner:{PASSWORD}@{HOST}/neondb?sslmode=require"
)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        print("Connected to Neon successfully!")
        print(result.fetchone()[0])
except Exception as e:
    print(f"Error: {e}")