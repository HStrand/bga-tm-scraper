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

IGNORED_TABLES = {"GamePlayerTrackerChanges"}

tables_df = pd.read_sql(
    "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
    "WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_SCHEMA, TABLE_NAME",
    conn,
)
tables_df = tables_df[~tables_df["TABLE_NAME"].isin(IGNORED_TABLES)]

print(f"Found {len(tables_df)} tables")

for _, row in tables_df.iterrows():
    schema = row["TABLE_SCHEMA"]
    table = row["TABLE_NAME"]
    filename = table.lower() + ".csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    print(f"Exporting [{schema}].[{table}] -> {filename} ... ", end="", flush=True)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM [{schema}].[{table}]")
    columns = [desc[0] for desc in cursor.description]
    total_rows = 0
    first_chunk = True
    while True:
        rows = cursor.fetchmany(50000)
        if not rows:
            break
        df = pd.DataFrame.from_records(rows, columns=columns)
        df.to_csv(filepath, index=False, mode="w" if first_chunk else "a", header=first_chunk)
        total_rows += len(df)
        first_chunk = False
    cursor.close()
    print(f"{total_rows} rows")

conn.close()
print("Done!")
