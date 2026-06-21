import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'aitreedoctor_mvp.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("UPDATE ai_models SET status='inactive'")
c.execute("UPDATE ai_models SET status='active' WHERE model_id='gemini-flash'")
conn.commit()
c.execute("SELECT model_id, status FROM ai_models")
print("Models:", c.fetchall())
conn.close()
