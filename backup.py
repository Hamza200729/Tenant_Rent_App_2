import os, datetime as dt, zipfile

SRC = "data/tenant.db"
# Adjust this path to your own Drive location if you use Google Drive for Desktop
DRIVE_BACKUP_DIR = os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/My Drive/TenantAppBackups")
os.makedirs(DRIVE_BACKUP_DIR, exist_ok=True)

ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
zip_path = os.path.join(DRIVE_BACKUP_DIR, f"tenantdb-{ts}.zip")

with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    z.write(SRC, arcname="tenant.db")

print("✅ Backup written:", zip_path)
