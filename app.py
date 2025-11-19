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
                   t.name AS tenant_name,
                   COALESCE((
                       SELECT i.status FROM invoices i
                       WHERE i.unit_id = u.id
                       ORDER BY i.due_date DESC LIMIT 1
                   ), 'unpaid') AS rent_status
            FROM units u
            LEFT JOIN tenants t ON t.id = u.current_tenant_id
            ORDER BY u.floor ASC, u.code ASC
        """, db())
    except Exception as e:
        st.error("Error loading building data. Please ensure tables are created.")
        building_data = pd.DataFrame()

    if building_data.empty:
        st.info("No rooms found. Please add units in the 'Units' tab.")
    else:
        floors = sorted(building_data["floor"].dropna().unique().tolist(), reverse=True)
        if not floors:
            floors = ["Ground", "1st", "2nd"]

        for floor in floors:
            st.markdown(f"### 🧱 Floor {floor}")
            floor_rooms = building_data[building_data["floor"] == floor]
            cols = st.columns(len(floor_rooms) if len(floor_rooms) > 0 else 2)

            for i, (_, room) in enumerate(floor_rooms.iterrows()):
                tenant = room["tenant_name"] or "Vacant"
                rent_status = room["rent_status"]
                
                if tenant == "Vacant":
                    status_color = "#A0A0A0"
                    rent_text = "— Vacant —"
                else:
                    status_color = "#25D366" if rent_status == "paid" else "#FF6961"
                    rent_text = "Paid" if rent_status == "paid" else "Unpaid"

                with cols[i]:
                    if st.button(f"🏠 {room['code']}", key=f"room_{room['id']}"):
                        st.session_state["selected_room"] = room["id"]

                    st.markdown(
                        f"""
                        <div class='room-card' style='border-color:{status_color}; border: 2px solid {status_color}; padding: 10px; border-radius: 5px; text-align: center;'>
                            <b>{tenant}</b><br>
                            <span style='color:{status_color};'>● {rent_text}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        if "selected_room" in st.session_state:
            rid = st.session_state["selected_room"]
            room_detail = pd.read_sql_query("""
                SELECT u.code, u.floor, u.rent_amount, u.status,
                       t.name AS tenant_name, t.phone, t.email
                FROM units u
                LEFT JOIN tenants t ON t.id = u.current_tenant_id
                WHERE u.id = ?
            """, db(), params=(rid,))
            
            if not room_detail.empty:
                r = room_detail.iloc[0]
                st.divider()
                st.markdown(f"### 🏠 Room {r['code']} — Details")
                st.markdown(f"**Floor:** {r['floor']}  |  **Rent:** ₹{int(r['rent_amount'] if r['rent_amount'] else 0)}")
                st.markdown(f"**Status:** {r['status'].capitalize()}")
                if r["tenant_name"]:
                    st.markdown(f"**Tenant:** {r['tenant_name']}")
                    st.markdown(f"📞 {r['phone'] or '-'}  |  📧 {r['email'] or '-'}")
            else:
                st.warning("Room details not found.")
    st.markdown("</div>", unsafe_allow_html=True)


# ==============================
# UNITS TAB
# ==============================
with tab_units:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🏢 Units / Rooms")

    with st.form("add_unit_form"):
        c1, c2 = st.columns(2)
        with c1:
            code = st.text_input("Code (e.g., G-101)")
            floor = st.text_input("Floor")
            size = st.text_input("Size")
        with c2:
            rent = st.number_input("Monthly Rent", min_value=0.0, step=100.0)
            deposit = st.number_input("Security Deposit", min_value=0.0, step=500.0)
        
        submitted = st.form_submit_button("Add Unit")
        
        if submitted:
            if code:
                run_query(
                    "INSERT INTO units(code,floor,size,rent_amount,deposit_amount,status) VALUES(?,?,?,?,?,'vacant')",
                    (code, floor, size, rent, deposit)
                )
                st.success(f"Room {code} added successfully.")
                st.rerun()
            else:
                st.error("Unit Code is required.")

    units = pd.read_sql_query("""
        SELECT u.id, u.code, u.floor, u.size, u.rent_amount, u.status,
               t.name AS tenant_name
        FROM units u
        LEFT JOIN tenants t ON t.id = u.current_tenant_id
        ORDER BY u.code
    """, db())

    if not units.empty:
        st.write("### Current Units")
        for _, u in units.iterrows():
            st.markdown(
                f"""
                <div class='unit-card' style='border:1px solid #ddd; padding:10px; margin:5px; border-radius:5px;'>
                    <b>{u['code']}</b> — {u['status'].capitalize()} | Floor: {u['floor'] or '-'} | Rent: ₹{int(u['rent_amount'] if u['rent_amount'] else 0)}
                    <br><small>Tenant: {u['tenant_name'] or '—'}</small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No units added yet.")
    st.markdown("</div>", unsafe_allow_html=True)
