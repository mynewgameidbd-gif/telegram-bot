# 🤖 Instagram Submission Bot

Telegram বট — Instagram/Facebook অ্যাকাউন্ট সাবমিশন সিস্টেম।

## 🎯 ফিচার
- ইউজার ফাইল সাবমিট
- ডায়নামিক ক্যাটাগরি ও রেট
- অটো Uid কাউন্ট
- অ্যাডমিন রিপোর্ট আপলোড (ok/of)
- অটো ব্যালেন্স ক্যালকুলেশন
- প্রতি আইডির জন্য অটো নোটিফিকেশন

## 🚀 Render Deployment

1. GitHub এ push করো
2. Render এ নতুন "Worker" সার্ভিস বানাও (দুইটা — user + admin)
3. Environment Variables সেট করো:
   - `USER_BOT_TOKEN`
   - `ADMIN_BOT_TOKEN`
   - `ADMIN_ID`

## 📁 ফাইল স্ট্রাকচার
- `config.py` — কনফিগ
- `database.py` — SQLite
- `file_processor.py` — Excel পার্সার
- `user_bot.py` — ইউজার বট
- `admin_bot.py` — অ্যাডমিন বট
