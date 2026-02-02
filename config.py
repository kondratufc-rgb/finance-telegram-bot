import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN", "").strip()

_raw_admins = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = {int(x.strip()) for x in _raw_admins.split(",") if x.strip().isdigit()}

if not TOKEN:
    raise RuntimeError("TOKEN is empty. Put TOKEN in .env file")
