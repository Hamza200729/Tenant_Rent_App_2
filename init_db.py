import sqlite3, os

os.makedirs("data", exist_ok=True)
con = sqlite3.connect("data/tenant.db")
cur = con.cursor()

cur.executescript("""
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS tenants(
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL,
 phone TEXT, email TEXT, photo_path TEXT, guarantor TEXT, notes TEXT,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS units(
 id INTEGER PRIMARY KEY,
 code TEXT UNIQUE NOT NULL,
 floor TEXT, size TEXT,
 rent_amount NUMERIC NOT NULL,
 deposit_amount NUMERIC DEFAULT 0,
 current_tenant_id INTEGER,
 status TEXT NOT NULL DEFAULT 'vacant',
 FOREIGN KEY(current_tenant_id) REFERENCES tenants(id)
);

CREATE TABLE IF NOT EXISTS invoices(
 id INTEGER PRIMARY KEY,
 tenant_id INTEGER, unit_id INTEGER,
 invoice_date DATE NOT NULL, due_date DATE, amount NUMERIC NOT NULL,
 description TEXT, status TEXT DEFAULT 'unpaid',
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(tenant_id) REFERENCES tenants(id),
 FOREIGN KEY(unit_id) REFERENCES units(id)
);

CREATE TABLE IF NOT EXISTS payments(
 id INTEGER PRIMARY KEY,
 tenant_id INTEGER, unit_id INTEGER,
 payment_date DATE NOT NULL, amount NUMERIC NOT NULL,
 purpose TEXT, payment_mode TEXT, reference TEXT, attachment_path TEXT,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(tenant_id) REFERENCES tenants(id),
 FOREIGN KEY(unit_id) REFERENCES units(id)
);

CREATE TABLE IF NOT EXISTS ledger_entries(
 id INTEGER PRIMARY KEY,
 tenant_id INTEGER, entry_date DATE NOT NULL, type TEXT NOT NULL,
 amount NUMERIC NOT NULL, running_balance NUMERIC, note TEXT, ref_id INTEGER,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(tenant_id) REFERENCES tenants(id)
);

CREATE TABLE IF NOT EXISTS electricity_bills(
 id INTEGER PRIMARY KEY,
 unit_id INTEGER, billing_period TEXT, total_amount NUMERIC,
 billed_date DATE, due_date DATE, split_method TEXT, status TEXT DEFAULT 'unpaid',
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(unit_id) REFERENCES units(id)
);
""")

con.commit()
con.close()
print("✅ Database created at data/tenant.db")
