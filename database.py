"""
Database — SQLite দিয়ে সব ডেটা ম্যানেজমেন্ট
Shared database — দুই বটই এটা ব্যবহার করে
"""
import sqlite3
from datetime import datetime
from config import DB_PATH


# ==================== DB INIT ====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Categories
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            columns TEXT DEFAULT 'Uid, Password',
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # Subcategories
    c.execute("""
        CREATE TABLE IF NOT EXISTS subcategories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            rate REAL DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    # Users
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance REAL DEFAULT 0,
            pending_balance REAL DEFAULT 0,
            total_income REAL DEFAULT 0,
            total_withdrawn REAL DEFAULT 0,
            completed_count INTEGER DEFAULT 0,
            in_review_count INTEGER DEFAULT 0,
            joined_at TEXT
        )
    """)

    # Submissions
    c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            category_id INTEGER,
            category_name TEXT,
            subcategory_id INTEGER,
            subcategory_name TEXT,
            rate REAL,
            file_name TEXT,
            file_id TEXT,
            account_count INTEGER DEFAULT 0,
            good_count INTEGER DEFAULT 0,
            bad_count INTEGER DEFAULT 0,
            preview TEXT,
            status TEXT DEFAULT 'pending',
            submitted_at TEXT,
            report_at TEXT
        )
    """)

    # Account Details (প্রতি Uid)
    c.execute("""
        CREATE TABLE IF NOT EXISTS account_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER,
            user_id INTEGER,
            uid TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)

    # Withdrawals
    c.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            amount REAL,
            method TEXT,
            account_number TEXT,
            status TEXT DEFAULT 'pending',
            requested_at TEXT
        )
    """)

    # Notifications Queue
    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            sent INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized")


# ==================== CATEGORY ====================
def add_category(name, columns="Uid, Password"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO categories (name, columns, active, created_at)
                     VALUES (?, ?, 1, ?)""",
                  (name, columns, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_all_categories(active_only=True):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if active_only:
        c.execute("SELECT id, name, columns FROM categories WHERE active=1 ORDER BY id")
    else:
        c.execute("SELECT id, name, columns FROM categories ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return rows


def get_category(cat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, columns, active FROM categories WHERE id=?", (cat_id,))
    row = c.fetchone()
    conn.close()
    return row


def delete_category(cat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM subcategories WHERE category_id=?", (cat_id,))
    c.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    conn.commit()
    conn.close()


def update_category_columns(cat_id, columns):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE categories SET columns=? WHERE id=?", (columns, cat_id))
    conn.commit()
    conn.close()


def rename_category(cat_id, new_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE categories SET name=? WHERE id=?", (new_name, cat_id))
    conn.commit()
    conn.close()


# ==================== SUBCATEGORY ====================
def add_subcategory(category_id, name, rate):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO subcategories (category_id, name, rate, active, created_at)
                 VALUES (?, ?, ?, 1, ?)""",
              (category_id, name, rate, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_subcategories(category_id, active_only=True):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if active_only:
        c.execute("SELECT id, name, rate FROM subcategories WHERE category_id=? AND active=1 ORDER BY id",
                  (category_id,))
    else:
        c.execute("SELECT id, name, rate FROM subcategories WHERE category_id=? ORDER BY id",
                  (category_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_subcategory(sub_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, category_id, name, rate, active FROM subcategories WHERE id=?", (sub_id,))
    row = c.fetchone()
    conn.close()
    return row


def delete_subcategory(sub_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM subcategories WHERE id=?", (sub_id,))
    conn.commit()
    conn.close()


def update_subcategory_rate(sub_id, rate):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE subcategories SET rate=? WHERE id=?", (rate, sub_id))
    conn.commit()
    conn.close()


# ==================== USER ====================
def add_user(user):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if not c.fetchone():
        c.execute("""INSERT INTO users 
            (user_id, username, full_name, balance, pending_balance, total_income,
             total_withdrawn, completed_count, in_review_count, joined_at)
            VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, ?)""",
                  (user.id, user.username, user.full_name,
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT user_id, username, full_name, balance, pending_balance,
                        total_income, total_withdrawn, completed_count, in_review_count
                 FROM users WHERE user_id=?""", (user_id,))
    row = c.fetchone()
    conn.close()
    return row


def get_all_user_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows


# ==================== SUBMISSION ====================
def save_submission(user, category, subcategory, file_name, file_id, count, preview, uids):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""INSERT INTO submissions 
        (user_id, username, full_name, category_id, category_name,
         subcategory_id, subcategory_name, rate, file_name, file_id,
         account_count, preview, status, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
        (user.id, user.username, user.full_name,
         category[0], category[1],
         subcategory[0], subcategory[1], subcategory[2],
         file_name, file_id, count, preview,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    submission_id = c.lastrowid

    for uid in uids:
        c.execute("""INSERT INTO account_details (submission_id, user_id, uid, status)
                     VALUES (?, ?, ?, 'pending')""",
                  (submission_id, user.id, uid))

    pending_earning = count * subcategory[2]
    c.execute("""UPDATE users 
                 SET in_review_count = in_review_count + ?,
                     pending_balance = pending_balance + ?
                 WHERE user_id=?""",
              (count, pending_earning, user.id))

    conn.commit()
    conn.close()
    return submission_id


def get_user_submissions(user_id, limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT id, category_name, subcategory_name, rate, file_name,
                        account_count, good_count, bad_count, status, submitted_at
                 FROM submissions WHERE user_id=?
                 ORDER BY id DESC LIMIT ?""", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


def get_user_report(user_id, limit=200):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT uid, status FROM account_details 
                 WHERE user_id=? AND status IN ('ok','of')
                 ORDER BY status DESC, id DESC LIMIT ?""", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


# ⭐⭐⭐ REPORT PROCESSING ⭐⭐⭐
def process_report_detailed(report_data):
    """
    report_data: dict { uid: 'ok' or 'of' }
    রিটার্ন: dict { user_id: {good, bad, earning, rate, category, subcategory, results} }
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""SELECT ad.id, ad.submission_id, ad.user_id, ad.uid,
                        s.rate, s.category_name, s.subcategory_name
                 FROM account_details ad
                 JOIN submissions s ON ad.submission_id = s.id
                 WHERE ad.status='pending'""")
    all_pending = c.fetchall()

    user_results = {}

    for acc_id, sub_id, user_id, uid, rate, cat_name, sub_name in all_pending:
        uid_clean = uid.strip()
        if uid_clean in report_data:
            status = report_data[uid_clean]
            c.execute("UPDATE account_details SET status=? WHERE id=?", (status, acc_id))

            if user_id not in user_results:
                user_results[user_id] = {
                    "good": 0, "bad": 0, "earning": 0,
                    "rate": rate,
                    "category": cat_name,
                    "subcategory": sub_name,
                    "submission_ids": set(),
                    "results": []
                }

            if status == "ok":
                user_results[user_id]["good"] += 1
            else:
                user_results[user_id]["bad"] += 1

            user_results[user_id]["results"].append((uid_clean, status))
            user_results[user_id]["submission_ids"].add(sub_id)

    for user_id, res in user_results.items():
        earning = res["good"] * res["rate"]
        c.execute("""UPDATE users 
                     SET balance = balance + ?,
                         total_income = total_income + ?,
                         pending_balance = MAX(0, pending_balance - ?),
                         in_review_count = MAX(0, in_review_count - ?),
                         completed_count = completed_count + ?
                     WHERE user_id=?""",
                  (earning, earning,
                   (res["good"] + res["bad"]) * res["rate"],
                   res["good"] + res["bad"],
                   res["good"] + res["bad"],
                   user_id))
        res["earning"] = earning

        for sub_id in res["submission_ids"]:
            c.execute("""UPDATE submissions 
                         SET good_count = good_count + ?,
                             bad_count = bad_count + ?,
                             status = 'completed',
                             report_at = ?
                         WHERE id=?""",
                      (res["good"], res["bad"],
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sub_id))

    conn.commit()
    conn.close()

    for uid, res in user_results.items():
        res.pop("submission_ids", None)

    return user_results


# ==================== WITHDRAWAL ====================
def save_withdrawal(user_id, username, amount, method, acc):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO withdrawals (user_id, username, amount, method, account_number, requested_at)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (user_id, username, amount, method, acc,
               datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


# ==================== NOTIFICATIONS ====================
def queue_notification(user_id, message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO notifications (user_id, message, sent, created_at)
                 VALUES (?, ?, 0, ?)""",
              (user_id, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_pending_notifications(limit=20):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT id, user_id, message FROM notifications 
                 WHERE sent=0 ORDER BY id LIMIT ?""", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def mark_notification_sent(notif_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE notifications SET sent=1 WHERE id=?", (notif_id,))
    conn.commit()
    conn.close()


# ==================== STATS ====================
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), COALESCE(SUM(account_count),0) FROM submissions")
    total_sub, total_acc = c.fetchone()
    c.execute("SELECT COUNT(DISTINCT user_id) FROM submissions")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'")
    pending_wd = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM submissions WHERE status='pending'")
    pending_sub = c.fetchone()[0]
    conn.close()
    return {
        "total_sub": total_sub, "total_acc": total_acc,
        "users": users, "pending_wd": pending_wd, "pending_sub": pending_sub,
  }
