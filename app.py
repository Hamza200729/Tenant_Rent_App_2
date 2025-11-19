import streamlit as st, sqlite3, pandas as pd, os, datetime as dt
from dateutil.relativedelta import relativedelta

# ==============================
# Database & Helpers
# ==============================
DB_PATH = "data/tenant.db"
os.makedirs("attachments", exist_ok=True)

def db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA foreign_keys=ON;")
    return con

def run_query(sql, params=()):
    con = db(); cur = con.cursor(); cur.execute(sql, params); con.commit(); return cur


# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(page_title="Tenant Manager", layout="wide")

# Load custom CSS
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


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

    if building_data.empty:
        st.info("No rooms found. Please add units first.")
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
                        <div class='room-card' style='border-color:{status_color};'>
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
                st.markdown(f"**Floor:** {r['floor']}  |  **Rent:** ₹{int(r['rent_amount'])}")
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

    code = st.text_input("Code (e.g., G-101)")
    rent = st.number_input("Monthly Rent", min_value=0.0, step=100.0)
    floor = st.text_input("Floor")
    size = st.text_input("Size")
    deposit = st.number_input("Security Deposit", min_value=0.0, step=500.0)
    if st.button("Add Unit"):
        run_query(
            "INSERT INTO units(code,floor,size,rent_amount,deposit_amount,status) VALUES(?,?,?,?,?,'vacant')",
            (code, floor, size, rent, deposit)
        )
        st.success(f"Room {code} added successfully.")
        st.rerun()

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
                <div class='unit-card'>
                    <b>{u['code']}</b> — {u['status'].capitalize()} | Floor: {u['floor'] or '-'} | Rent: ₹{int(u['rent_amount'])}
                    <br><small>Tenant: {u['tenant_name'] or '—'}</small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No units added yet.")
    st.markdown("</div>", unsafe_allow_html=True)
