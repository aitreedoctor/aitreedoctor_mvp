import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "aitreedoctor_mvp.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get the latest diagnosis
cursor.execute("SELECT id, tree_species, suspected_disease, pesticide_prescription FROM diagnoses ORDER BY created_at DESC LIMIT 1;")
row = cursor.fetchone()
if not row:
    print("No diagnosis found.")
    exit()

diag_id, tree_species, suspected_disease, pesticide_prescription = row
print(f"Latest ID: {diag_id}")
print(f"Tree Species: {repr(tree_species)}")
print(f"Suspected Disease: {repr(suspected_disease)}")
print(f"Prescription: {repr(pesticide_prescription)}")

# Re-run the query
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
