import streamlit as st, sqlite3, pandas as pd, os, datetime as dt

# ==============================
# 1. DATABASE & SETUP
# ==============================
# We use the root folder so it works easily on GitHub
DB_PATH = "tenant.db"

# Ensure attachments folder exists
os.makedirs("attachments", exist_ok=True)

def db():
    """Connect to the database."""
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.execute("PRAGMA foreign_keys=ON;")
    return con

def init_db():
    """
    Initialize database tables.
    This runs automatically to ensure the app doesn't crash on new installs.
    """
    con = db()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            joined_date DATE DEFAULT CURRENT_DATE
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
            description TEXT,
            status TEXT DEFAULT 'unpaid',
            due_date DATE,
            FOREIGN KEY(unit_id) REFERENCES units(id),
            FOREIGN KEY(tenant_id) REFERENCES tenants(id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER,
            unit_id INTEGER,
            amount REAL,
            date DATE,
            method TEXT,
            FOREIGN KEY(tenant_id) REFERENCES tenants(id),
            FOREIGN KEY(unit_id) REFERENCES units(id)
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

# Run initialization immediately
if not os.path.exists(DB_PATH):
    init_db()
else:
    # Run it anyway to ensure missing tables (like payments) are added
    init_db()


# ==============================
# 2. PAGE CONFIG & STYLING
# ==============================
st.set_page_config(page_title="Tenant Manager", layout="wide")

# Load custom CSS if it exists, otherwise use default
css_file = "style.css"
if os.path.exists(css_file):
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .card {padding: 20px; border-radius: 10px; background: #f9f9f9; margin-bottom: 20px; border: 1px solid #ddd;}
        .unit-card {padding: 10px; border: 1px solid #ddd; margin-bottom: 10px; border-radius: 5px;}
        .success {color: #25D366;}
        .danger {color: #FF6961;}
    </style>
    """, unsafe_allow_html=True)


# ==============================
# 3. HEADER & TABS
# ==============================
st.markdown("""
<header>
  <h1>🏢 City Tenant Management Dashboard</h1>
</header>
""", unsafe_allow_html=True)

tab_dash, tab_units, tab_tenants, tab_invoices, tab_pay, tab_ledger = st.tabs(
    ["🏠 Dashboard","🏢 Units","👥 Tenants","📄 Invoices","💰 Payments","📘 Ledger"]
)


# ==============================
# TAB 1: DASHBOARD
# ==============================
with tab_dash:
    st.subheader("🏙️ Building Overview")
    try:
        building_data = pd.read_sql_query("""
            SELECT u.id, u.code, u.floor, u.status, u.rent_amount,
                   t.name AS tenant_name,
                   COALESCE((SELECT status FROM invoices WHERE unit_id = u.id ORDER BY due_date DESC LIMIT 1), 'unpaid') AS rent_status
            FROM units u
            LEFT JOIN tenants t ON t.id = u.current_tenant_id
            ORDER BY u.floor, u.code
        """, db())
    except:
        building_data = pd.DataFrame()

    if not building_data.empty:
        floors = sorted(building_data["floor"].dropna().unique().tolist())
        for floor in floors:
            st.markdown(f"### Floor {floor}")
            floor_rooms = building_data[building_data["floor"] == floor]
            cols = st.columns(5)
            for i, (_, room) in enumerate(floor_rooms.iterrows()):
                with cols[i % 5]:
                    status_color = "#28a745" if room['rent_status'] == 'paid' else "#dc3545"
                    if room['status'] == 'vacant': status_color = "#6c757d"
                    
                    st.markdown(f"""
                    <div style='border: 2px solid {status_color}; padding: 10px; border-radius: 8px; text-align: center;'>
                        <strong>{room['code']}</strong><br>
                        <small>{room['tenant_name'] or 'Vacant'}</small>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("No units found. Add them in the Units tab.")


# ==============================
# TAB 2: UNITS
# ==============================
with tab_units:
    st.subheader("Add New Unit")
    with st.form("unit_form"):
        c1, c2, c3 = st.columns(3)
        code = c1.text_input("Unit Code (e.g., 101)")
        floor = c2.text_input("Floor (e.g., 1st)")
        rent = c3.number_input("Rent Amount", min_value=0)
        if st.form_submit_button("Add Unit"):
            run_query("INSERT INTO units (code, floor, rent_amount) VALUES (?,?,?)", (code, floor, rent))
            st.success("Unit Added!")
            st.rerun()

    st.subheader("Existing Units")
    units = pd.read_sql_query("SELECT * FROM units", db())
    st.dataframe(units)


# ==============================
# TAB 3: TENANTS (With Delete)
# ==============================
with tab_tenants:
    # Create 3 columns for Add, Assign, and Delete
    c1, c2, c3 = st.columns([1, 1, 1])
    
    # --- SECTION 1: ADD TENANT ---
    with c1:
        st.markdown("### 1. Add Tenant")
        with st.form("add_tenant"):
            t_name = st.text_input("Full Name")
            t_phone = st.text_input("Phone")
            t_email = st.text_input("Email")
            if st.form_submit_button("Create Profile"):
                if t_name:
                    run_query("INSERT INTO tenants (name, phone, email) VALUES (?,?,?)", (t_name, t_phone, t_email))
                    st.success(f"Tenant {t_name} created.")
                    st.rerun()
                else:
                    st.error("Name required")

    # --- SECTION 2: ASSIGN TO UNIT ---
    with c2:
        st.markdown("### 2. Assign to Unit")
        vacant_units = pd.read_sql_query("SELECT id, code FROM units WHERE status='vacant'", db())
        all_tenants = pd.read_sql_query("SELECT id, name FROM tenants", db())

        if not vacant_units.empty and not all_tenants.empty:
            with st.form("assign_form"):
                u_idx = st.selectbox("Select Unit", vacant_units['id'], format_func=lambda x: vacant_units[vacant_units['id']==x]['code'].values[0])
                t_idx = st.selectbox("Select Tenant", all_tenants['id'], format_func=lambda x: all_tenants[all_tenants['id']==x]['name'].values[0])
                
                if st.form_submit_button("Assign & Move In"):
                    run_query("UPDATE units SET status='occupied', current_tenant_id=? WHERE id=?", (t_idx, u_idx))
                    st.success("Tenant moved in successfully!")
                    st.rerun()
        else:
            st.info("Need Vacant Unit & Tenant Profile to assign.")

    # --- SECTION 3: DELETE TENANT ---
    with c3:
        st.markdown("### 3. Delete Tenant")
        
        tenants_to_delete = pd.read_sql_query("SELECT id, name FROM tenants", db())
        
        if not tenants_to_delete.empty:
            with st.form("delete_tenant_form"):
                del_id = st.selectbox("Select Tenant to Delete", tenants_to_delete['id'], format_func=lambda x: tenants_to_delete[tenants_to_delete['id']==x]['name'].values[0])
                
                # Warning checkbox
                delete_history = st.checkbox("Delete all financial history?", value=False, help="Checking this will delete all Invoices and Payments associated with this tenant.")
                
                if st.form_submit_button("Delete Tenant"):
                    try:
                        # 1. Vacate any unit they are currently in
                        run_query("UPDATE units SET status='vacant', current_tenant_id=NULL WHERE current_tenant_id=?", (del_id,))
                        
                        # 2. Optional: Delete financial history if checked
                        if delete_history:
                            run_query("DELETE FROM invoices WHERE tenant_id=?", (del_id,))
                            run_query("DELETE FROM payments WHERE tenant_id=?", (del_id,))
                        
                        # 3. Delete the tenant profile
                        run_query("DELETE FROM tenants WHERE id=?", (del_id,))
                        
                        st.success("Tenant deleted.")
                        st.rerun()
                        
                    except Exception as e:
                        st.error("Could not delete tenant.")
                        st.warning("This tenant likely has invoices/payments. Check the box above to force delete them.")
        else:
            st.info("No tenants available.")

    st.divider()
    st.subheader("Tenant Directory")
    t_data = pd.read_sql_query("""
        SELECT t.id, t.name, t.phone, t.email, u.code as current_unit
        FROM tenants t
        LEFT JOIN units u ON u.current_tenant_id = t.id
    """, db())
    st.dataframe(t_data, use_container_width=True)


# ==============================
# TAB 4: INVOICES
# ==============================
with tab_invoices:
    st.subheader("Generate Rent Invoice")
    
    occupied = pd.read_sql_query("""
        SELECT u.id, u.code, u.rent_amount, t.name, t.id as tenant_id 
        FROM units u 
        JOIN tenants t ON u.current_tenant_id = t.id 
        WHERE u.status='occupied'
    """, db())

    if not occupied.empty:
        with st.form("inv_form"):
            unit_sel = st.selectbox("Select Unit", occupied['id'], format_func=lambda x: f"{occupied[occupied['id']==x]['code'].values[0]} - {occupied[occupied['id']==x]['name'].values[0]}")
            
            selected_row = occupied[occupied['id'] == unit_sel].iloc[0]
            amount = st.number_input("Amount", value=float(selected_row['rent_amount']))
            due_date = st.date_input("Due Date", dt.date.today())
            desc = st.text_input("Description", "Monthly Rent")
            
            if st.form_submit_button("Create Invoice"):
                run_query("""
                    INSERT INTO invoices (unit_id, tenant_id, amount, description, due_date, status)
                    VALUES (?, ?, ?, ?, ?, 'unpaid')
                """, (int(selected_row['id']), int(selected_row['tenant_id']), amount, desc, due_date))
                st.success("Invoice Generated")
                st.rerun()
    else:
        st.warning("No occupied units found.")

    st.subheader("Recent Invoices")
    try:
        invs = pd.read_sql_query("SELECT * FROM invoices ORDER BY id DESC", db())
        st.dataframe(invs)
    except:
        st.write("No invoices yet.")


# ==============================
# TAB 5: PAYMENTS
# ==============================
with tab_pay:
    st.subheader("Record Payment")
    
    try:
        unpaid = pd.read_sql_query("""
            SELECT i.id, i.amount, u.code, t.name, i.unit_id, i.tenant_id
            FROM invoices i
            JOIN units u ON i.unit_id = u.id
            JOIN tenants t ON i.tenant_id = t.id
            WHERE i.status = 'unpaid'
        """, db())
    except:
        unpaid = pd.DataFrame()

    if not unpaid.empty:
        with st.form("pay_form"):
            inv_id = st.selectbox("Select Invoice", unpaid['id'], format_func=lambda x: f"Inv #{x} - {unpaid[unpaid['id']==x]['name'].values[0]} - ₹{unpaid[unpaid['id']==x]['amount'].values[0]}")
            
            row = unpaid[unpaid['id'] == inv_id].iloc[0]
            pay_amt = st.number_input("Payment Amount", value=float(row['amount']))
            pay_date = st.date_input("Date", dt.date.today())
            
            if st.form_submit_button("Record Payment"):
                run_query("INSERT INTO payments (tenant_id, unit_id, amount, date, method) VALUES (?,?,?,?, 'Cash')", 
                          (int(row['tenant_id']), int(row['unit_id']), pay_amt))
                
                run_query("UPDATE invoices SET status='paid' WHERE id=?", (int(inv_id),))
                st.success("Payment Recorded!")
                st.rerun()
    else:
        st.info("No pending invoices.")


# ==============================
# TAB 6: LEDGER
# ==============================
with tab_ledger:
    st.subheader("📘 Tenant Ledger")
    
    try:
        tenants_list = pd.read_sql_query("SELECT id, name FROM tenants", db())
        
        if not tenants_list.empty:
            selected_t_id = st.selectbox("Select Tenant for Ledger", tenants_list['id'], format_func=lambda x: tenants_list[tenants_list['id']==x]['name'].values[0])
            
            if selected_t_id:
                # We use a TRY block here so the app doesn't crash if the 'payments' table 
                # is missing (common issue when updating code on GitHub).
                try:
                    debits = pd.read_sql_query(f"SELECT due_date as Date, description as Item, amount as Debit, 0 as Credit FROM invoices WHERE tenant_id={selected_t_id}", db())
                    credits = pd.read_sql_query(f"SELECT date as Date, 'Payment Received' as Item, 0 as Debit, amount as Credit FROM payments WHERE tenant_id={selected_t_id}", db())
                    
                    ledger = pd.concat([debits, credits]).sort_values(by="Date")
                    ledger['Balance'] = (ledger['Debit'] - ledger['Credit']).cumsum()
                    
                    st.dataframe(ledger, use_container_width=True)
                    
                    total_due = ledger['Debit'].sum() - ledger['Credit'].sum()
                    if total_due > 0:
                        st.error(f"Outstanding Balance: ₹{total_due}")
                    else:
                        st.success(f"Balance Cleared: ₹{total_due}")

                except Exception as e:
                    st.warning("⚠️ Database is updating...")
                    st.info("If you see this, please restart the app or delete 'tenant.db' from the repo to reset the database structure.")
    except Exception:
        st.info("No tenants found.")
