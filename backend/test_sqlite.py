import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "aitreedoctor_mvp.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

tree_species = "느티나무 (Zelkova serrata)"
suspected_disease = "부후 (Wood rot disease) 및 공동 형성 (Trunk cavity formation)"

cursor.execute("""
SELECT product_name, active_ingredient, dilution_ratio, safety_standard 
FROM pesticide_registry 
WHERE ? LIKE '%' || crop_name || '%' AND ? LIKE '%' || disease_name || '%'
""", (tree_species, suspected_disease))

rows = cursor.fetchall()
print(f"Matched rows: {len(rows)}")
for r in rows:
    print(r)
conn.close()
