import streamlit as st, sqlite3, pandas as pd, os, datetime as dt
from dateutil.relativedelta import relativedelta

# ==============================
# Database & Helpers
# ==============================

# CHANGE 1: Updated path to root directory (removed "data/")
DB_PATH = "tenant.db"

# Ensure attachments folder exists for file uploads
os.makedirs("attachments", exist_ok=True)

def db():
    """Connect to the database."""
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA foreign_keys=ON;")
    return con

def init_db():
    """
    CHANGE 2: Create tables if they don't exist. 
    This ensures the app doesn't crash if the DB file is missing or empty on GitHub.
    """
    con = db()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            floor TEXT,
            size TEXT,
            rent_amount REAL,
            deposit_amount REAL,
            status TEXT DEFAULT 'vacant',
            current_tenant_id INTEGER,
            FOREIGN KEY(current_tenant_id) REFERENCES tenants(id)
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER,
            tenant_id INTEGER,
            amount REAL,
            status TEXT DEFAULT 'unpaid',
            due_date DATE,
            FOREIGN KEY(unit_id) REFERENCES units(id),
            FOREIGN KEY(tenant_id) REFERENCES tenants(id)
        );
    """)
    con.commit()
    con.close()

def run_query(sql, params=()):
    """Run a write query (INSERT/UPDATE/DELETE)."""
    con = db()
    cur = con.cursor()
    try:
        cur.execute(sql, params)
        con.commit()
        return cur
    except Exception as e:
        st.error(f"Database Error: {e}")
        return None

# Initialize DB structure on script load
if not os.path.exists(DB_PATH):
    init_db()
else:
    # Double check tables exist even if file exists
    init_db()


# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(page_title="Tenant Manager", layout="wide")

# Load custom CSS (Make sure style.css is also in the root folder)
css_file = "style.css"
if os.path.exists(css_file):
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    # Fallback CSS if style.css is missing
    st.markdown("<style>.card {padding: 20px; border-radius: 10px; background: #f9f9f9; margin-bottom: 20px;}</style>", unsafe_allow_html=True)


# ==============================
# HEADER SECTION
# ==============================
st.markdown("""
<header>
  <h1>🏢 City Tenant Management Dashboard</h1>
  <p>Simplify your property, rent, and billing workflow.</p>
</header>
""", unsafe_allow_html=True)


# ==============================
# NAVIGATION TABS
# ==============================
tab_dash, tab_units, tab_tenants, tab_invoices, tab_pay, tab_ledger, tab_reports = st.tabs(
    ["🏠 Dashboard","🏢 Units","👥 Tenants","📄 Invoices","💰 Payments","📘 Ledger","📊 Reports"]
)


# ==============================
# DASHBOARD TAB
# ==============================
with tab_dash:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🏙️ Building Overview")

    # We use try/except here just in case the schema is still updating
    try:
        building_data = pd.read_sql_query("""
            SELECT u.id, u.code, u.floor, u.status, u.rent_amount,
