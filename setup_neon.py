import os

os.environ['DB_HOST'] = 'ep-wild-salad-an3s1bki-pooler.c-6.us-east-1.aws.neon.tech'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'neondb'
os.environ['DB_USER'] = 'neondb_owner'
os.environ['DB_PASSWORD'] = 'npg_sA9UbkCrJ4mf'
os.environ['APP_DEBUG'] = 'False'

from sqlalchemy import create_engine, text

engine = create_engine(
    "postgresql://neondb_owner:npg_sA9UbkCrJ4mf@ep-wild-salad-an3s1bki-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"
)

# Read and run schema
with open('schema.sql', 'r') as f:
    schema = f.read()

with engine.connect() as conn:
    conn.execute(text(schema))
    conn.commit()
    print("Schema created on Neon!")

# Now seed data
from app.database.db import get_session, create_all_tables
from app.database.seed import run_seed
run_seed()
print("Data seeded on Neon!")