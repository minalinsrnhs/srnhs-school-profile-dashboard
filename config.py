import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXCEL_DIR = BASE_DIR / "excel"
LOCAL_DB_PATH = Path(os.environ.get("LOCAL_DB_PATH", str(DATA_DIR / "srnhs_local.db")))
DATA_BACKEND = os.environ.get("DATA_BACKEND", "sqlite").strip().lower()
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "local-preview-change-before-publishing")
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
FIRST_ACCOUNT_NAME = os.environ.get("FIRST_ACCOUNT_NAME", "SRNHS Admin")
FIRST_ACCOUNT_USERNAME = os.environ.get("FIRST_ACCOUNT_USERNAME", "admin")
FIRST_ACCOUNT_PASSWORD = os.environ.get("FIRST_ACCOUNT_PASSWORD", "srnhsadmin")
TEMPLATE_FILE = EXCEL_DIR / "SRNHS_Dashboard_Data_Simple_Editable.xlsx"
NEW_YEAR_TEMPLATE_FILE = EXCEL_DIR / "SRNHS_New_School_Year_Upload_Template.xlsx"
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "25"))
