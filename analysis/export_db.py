import json
import pyodbc
import pandas as pd
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db_config.json")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db_dump")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    db = json.load(f)

conn = pyodbc.connect(
    f"Driver={{{db['driver']}}};"
    f"Server={db['server']};"
    f"Database={db['database']};"
    f"Uid={db['username']};"
    f"Pwd={db['password']};"
    f"Encrypt={db['encrypt']};"
    f"TrustServerCertificate={db['trust_server_certificate']};"
)

tables_df = pd.read_sql(
    "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
    "WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_SCHEMA, TABLE_NAME",
    conn,
)

print(f"Found {len(tables_df)} tables")

for _, row in tables_df.iterrows():
    schema = row["TABLE_SCHEMA"]
    table = row["TABLE_NAME"]
    filename = table.lower() + ".csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    print(f"Exporting [{schema}].[{table}] -> {filename} ... ", end="", flush=True)
    df = pd.read_sql(f"SELECT * FROM [{schema}].[{table}]", conn)
    df.to_csv(filepath, index=False)
    print(f"{len(df)} rows")

conn.close()
print("Done!")
