import psycopg2

LOCAL_DB_URL = "postgresql://postgres:MyDbAdmin**@localhost:5433/shopbygold"
LIVE_DB_URL = "password".replace("postgres://", "postgresql://")

local_conn = psycopg2.connect(LOCAL_DB_URL)
live_conn = psycopg2.connect(LIVE_DB_URL)
local_conn.autocommit = True
live_conn.autocommit = True

local_cur = local_conn.cursor()
live_cur = live_conn.cursor()

# Get tables that exist on LIVE
live_cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
live_tables = [r[0] for r in live_cur.fetchall()]
print(f"Live tables: {live_tables}")

# Clear only tables that exist on LIVE
if live_tables:
    tables_to_clear = ', '.join([f'"{t}"' for t in live_tables])
    try:
        live_cur.execute(f'TRUNCATE {tables_to_clear} CASCADE')
        print("Live DB cleared!")
    except Exception as e:
        print(f"Clear warning: {e}")
        live_conn.rollback()

# Copy in parent-first order
order = ["users", "products", "settings", "shipping_fee", "cart", "orders", "order_items", "cart_item", "review", "password_reset_tokens"]

for table in order:
    if table not in live_tables:
        print(f"\n{live_tables} doesn't have {table}, skipping")
        continue
    print(f"\nCopying {table}...")
    try:
        local_cur.execute(f'SELECT * FROM "{table}"')
        rows = local_cur.fetchall()
        if not rows:
            print(" empty")
            continue
        cols = [desc[0] for desc in local_cur.description]
        col_list = ', '.join([f'"{c}"' for c in cols])
        placeholders = ', '.join(['%s'] * len(cols))
        count = 0
        for row in rows:
            try:
                live_cur.execute(f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})', row)
                count += 1
            except Exception as e:
                live_conn.rollback()
        print(f" ✅ {count}/{len(rows)} rows -> {table}")
    except Exception as e:
        print(f" Skip {table}: {e}")

print("\n✅ DONE! Try login now on your live site!")