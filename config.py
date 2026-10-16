"""
Configuration — সব Token ও Setting এখানে
Render Environment Variables থেকে পড়বে
"""
import os

# ============ BOT TOKENS ============
# Render এ Environment Variable হিসেবে সেট করবে
# Local এ চালাতে চাইলে .env ফাইলে রাখবে

USER_BOT_TOKEN = os.environ.get("8947059922:AAHHJlU8FrzE86RKm8M4pJ5yP4wCXUcqrLc", "")
ADMIN_BOT_TOKEN = os.environ.get("8969451047:AAEtBROQDxDB-8FniVTr5-WYGzcmt_K-Ijc", "")

# ============ ADMIN ID ============
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# ============ DATABASE ============
DB_PATH = os.environ.get("DB_PATH", "bot_data.db")

# ============ VALIDATION ============
if not USER_BOT_TOKEN:
    raise ValueError("❌ USER_BOT_TOKEN সেট করা হয়নি!")
if not ADMIN_BOT_TOKEN:
    raise ValueError("❌ ADMIN_BOT_TOKEN সেট করা হয়নি!")
if not ADMIN_ID:
    raise ValueError("❌ ADMIN_ID সেট করা হয়নি!")
