import sqlite3

DB = "quizbot.sqlite3"
con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("PRAGMA table_info(users);")
cols = [row[1] for row in cur.fetchall()]
print("Users columns:", cols)

if "is_superadmin" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN is_superadmin INTEGER NOT NULL DEFAULT 0;")
    con.commit()
    print("✅ is_superadmin column qo‘shildi")
else:
    print("✅ is_superadmin allaqachon bor")

con.close()