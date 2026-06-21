import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "aitreedoctor_mvp.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. diagnoses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS diagnoses (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        tree_species TEXT NOT NULL,
        suspected_disease TEXT NOT NULL,
        confidence_score REAL NOT NULL,
        severity_level TEXT NOT NULL,
        immediate_actions TEXT NOT NULL,
        address TEXT,
        pdf_url TEXT,
        status_leaves TEXT,
        status_stems TEXT,
        status_roots TEXT,
        treatment_method TEXT,
        pesticide_prescription TEXT,
        status_leaves_summary TEXT,
        status_stems_summary TEXT,
        status_roots_summary TEXT,
        treatment_method_summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Migration: Add columns if database already exists
    migration_columns = [
        ("address", "TEXT"),
        ("status_leaves", "TEXT"),
        ("status_stems", "TEXT"),
        ("status_roots", "TEXT"),
        ("treatment_method", "TEXT"),
        ("pesticide_prescription", "TEXT"),
        ("status_leaves_summary", "TEXT"),
        ("status_stems_summary", "TEXT"),
        ("status_roots_summary", "TEXT"),
        ("treatment_method_summary", "TEXT")
    ]
    for col_name, col_type in migration_columns:
        try:
            cursor.execute(f"ALTER TABLE diagnoses ADD COLUMN {col_name} {col_type};")
        except sqlite3.OperationalError:
            pass # Column already exists

    
    # 2. pesticide_registry table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pesticide_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crop_name TEXT NOT NULL,
        disease_name TEXT NOT NULL,
        product_name TEXT NOT NULL,
        active_ingredient TEXT NOT NULL,
        dilution_ratio TEXT NOT NULL,
        safety_standard TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_crop_disease ON pesticide_registry(crop_name, disease_name);")
    
    # Clear and re-populate the pesticide registry to include updated treatment entries
    cursor.execute("DELETE FROM pesticide_registry")
    pesticides = [
        ("소나무", "소나무잎응애", "밀베멕틴 유제", "밀베멕틴 1.0%", "물 20L당 20ml 희석 (1,000배액)", "발생 초엽 수관 살포, 10일 간격 2회 이내"),
        ("소나무", "소나무재선충병", "아바멕틴 액제", "아바멕틴 1.8%", "원액 수간주사 (경급 cm당 1ml)", "우화기 전 수간주사, 연 1회"),
        ("소나무", "소나무재선충병", "에마멕틴벤조에이트 유제", "에마멕틴벤조에이트 2.15%", "원액 또는 희석 수간주사", "동절기(11월~2월) 수간주사"),
        ("느티나무", "벼룩바구미", "이미다클로프리드 액제", "이미다클로프리드 8%", "원액 수간주사", "발생 초기 수간주사"),
        ("벚나무", "갈색무늬구멍병", "티오파네이트메틸 수화물", "티오파네이트메틸 70%", "물 20L당 20g 희석 (1,000배액)", "발엽기 가을 전 3회 이내"),
        # 신규 추가: 수목 외과수술(줄기/수간 부후병)에 대응하는 등록 약제
        ("소나무", "부후", "티오파네이트메틸 도포제", "티오파네이트메틸 3%", "도포제 원액 직접 도포 (환부 외과수술 후 도포)", "상처 처치 및 외과수술 부후부 도포, 연 1회"),
        ("소나무", "부후", "테부코나졸 수화물", "테부코나졸 25%", "물 20L당 10g 희석 (2,000배액) 환부 분무", "외과수술 후 소독 및 살균, 상처 부위 처리"),
        ("느티나무", "부후", "티오파네이트메틸 도포제", "티오파네이트메틸 3%", "도포제 원액 직접 도포 (환부 외과수술 후 도포)", "상처 처치 및 외과수술 부후부 도포, 연 1회"),
        ("느티나무", "부후", "테부코나졸 수화물", "테부코나졸 25%", "물 20L당 10g 희석 (2,000배액) 환부 분무", "외과수술 후 소독 및 살균, 상처 부위 처리"),
        ("벚나무", "부후", "티오파네이트메틸 도포제", "티오파네이트메틸 3%", "도포제 원액 직접 도포 (환부 외과수술 후 도포)", "상처 처치 및 외과수술 부후부 도포, 연 1회"),
        ("벚나무", "부후", "테부코나졸 수화물", "테부코나졸 25%", "물 20L당 10g 희석 (2,000배액) 환부 분무", "외과수술 후 소독 및 살균, 상처 부위 처리"),
    ]
    cursor.executemany("""
    INSERT INTO pesticide_registry (crop_name, disease_name, product_name, active_ingredient, dilution_ratio, safety_standard)
    VALUES (?, ?, ?, ?, ?, ?)
    """, pesticides)
    
    # 3. ai_models table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_models (
        model_id TEXT PRIMARY KEY,
        model_name TEXT NOT NULL,
        dataset_size INTEGER NOT NULL,
        epochs INTEGER NOT NULL,
        accuracy REAL NOT NULL,
        loss REAL NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Seed default models if table is empty
    cursor.execute("SELECT COUNT(*) FROM ai_models")
    if cursor.fetchone()[0] == 0:
        default_models = [
            ("gemini-flash", "Gemini 1.5 Flash (Cloud)", 0, 0, 0.95, 0.05, "active"),
            ("resnet50-local", "ResNet50 v1.0 (Local Edge)", 12500, 10, 0.912, 0.245, "inactive")
        ]
        cursor.executemany("""
        INSERT INTO ai_models (model_id, model_name, dataset_size, epochs, accuracy, loss, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, default_models)
        
    # 4. ncpms_knowledge table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ncpms_knowledge (
        sick_key TEXT PRIMARY KEY,
        crop_name TEXT NOT NULL,
        sick_name_kor TEXT NOT NULL,
        development_env TEXT,
        symptoms TEXT,
        prevention_method TEXT,
        image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
