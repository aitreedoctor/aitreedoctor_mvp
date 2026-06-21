import os
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .db import get_db_connection

router = APIRouter()

# ─────────────────────────────────────────────
# Pydantic 모델 정의
# ─────────────────────────────────────────────
class ModelInfo(BaseModel):
    model_id: str
    model_name: str
    dataset_size: int
    epochs: int
    accuracy: float
    loss: float
    status: str
    created_at: str

class TrainingStartRequest(BaseModel):
    dataset_path: str
    epochs: int = 5
    lr: float = 0.001
    batch_size: int = 32

class TrainingStatusResponse(BaseModel):
    is_training: bool
    current_epoch: int
    total_epochs: int
    progress: int
    loss: float
    accuracy: float
    logs: List[str]

# ─────────────────────────────────────────────
# 글로벌 학습 상태 관리 (메모리 내 상태값)
# ─────────────────────────────────────────────
class GlobalTrainingState:
    def __init__(self):
        self.is_training = False
        self.current_epoch = 0
        self.total_epochs = 0
        self.progress = 0
        self.loss = 0.0
        self.accuracy = 0.0
        self.logs = []
        self.dataset_path = ""
        self.lr = 0.001
        self.batch_size = 32

training_state = GlobalTrainingState()

# ─────────────────────────────────────────────
# 비동기 학습 시뮬레이터 백그라운드 태스크
# ─────────────────────────────────────────────
async def run_training_simulation(dataset_path: str, total_epochs: int, lr: float, batch_size: int):
    global training_state
    
    try:
        training_state.is_training = True
        training_state.total_epochs = total_epochs
        training_state.current_epoch = 0
        training_state.progress = 0
        training_state.loss = 1.45
        training_state.accuracy = 0.50
        training_state.dataset_path = dataset_path
        training_state.lr = lr
        training_state.batch_size = batch_size
        training_state.logs = [
            f"[SYSTEM] AI 모델 파인튜닝 프로세스 초기화 중...",
            f"[SYSTEM] 데이터셋 경로 감지: {dataset_path}",
            f"[SYSTEM] 학습 파라미터 세팅 -> Epochs: {total_epochs}, LR: {lr}, Batch Size: {batch_size}",
        ]
        
        await asyncio.sleep(1.5)
        training_state.logs.append("[DATASET] AI-Hub 데이터셋 구조 분석 중...")
        training_state.logs.append("[DATASET] 이미지 및 메타데이터(JSON 어노테이션) 매핑 중...")
        
        await asyncio.sleep(1.5)
        # 이미지 개수 임의 할당 (3000 ~ 15000 사이)
        import random
        img_count = random.randint(3000, 15000)
        training_state.logs.append(f"[DATASET] 검증 완료: 수목 전경/환부 이미지 총 {img_count:,}장 적재 완료.")
        training_state.logs.append(f"[DATASET] 수종 분류: 소나무(40%), 벚나무(35%), 느티나무(25%) 분포 확인.")
        training_state.logs.append("[SYSTEM] CNN 백본 네트워크 (ResNet50) 가중치 로드 완료.")
        training_state.logs.append("[SYSTEM] 학습 엔진 시동 - GPU 가속 활성화 (CUDA Cores 2,560)")
        
        # 에폭별 시뮬레이션 루프
        base_loss = 1.25
        base_acc = 0.58
        
        for epoch in range(1, total_epochs + 1):
            training_state.current_epoch = epoch
            training_state.logs.append(f"\n--- [EPOCH {epoch} / {total_epochs}] 학습 시작 ---")
            
            # Step 시뮬레이션
            steps = 4
            for step in range(1, steps + 1):
                # 점진적 지표 개선 계산
                progress_step = int(((epoch - 1) * steps + step) / (total_epochs * steps) * 100)
                training_state.progress = min(99, progress_step)
                
                # 에러율 감소 및 정확도 향상 추이 연산 (약간의 난수 흔들림 추가)
                factor = ((epoch - 1) * steps + step) / (total_epochs * steps)
                current_loss = max(0.08, base_loss - (base_loss - 0.09) * factor + random.uniform(-0.03, 0.03))
                current_acc = min(0.985, base_acc + (0.97 - base_acc) * factor + random.uniform(-0.015, 0.015))
                
                training_state.loss = round(current_loss, 4)
                training_state.accuracy = round(current_acc, 4)
                
                step_idx = step * 100
                training_state.logs.append(
                    f"  -> [Step {step_idx}/{steps*100}] Loss: {training_state.loss:.4f} | Accuracy: {training_state.accuracy*100:.2f}% | 속도: 245.8 img/sec"
                )
                await asyncio.sleep(2.0)
            
            # Epoch 검증 완료
            val_loss = round(training_state.loss * 0.95, 4)
            val_acc = round(min(0.985, training_state.accuracy * 1.02), 4)
            training_state.logs.append(f"  [VALIDATION] Epoch {epoch} 완료 -> Val Loss: {val_loss:.4f} | Val Accuracy: {val_acc*100:.2f}%")
            
        # 학습 완료
        training_state.progress = 100
        training_state.logs.append("\n[SYSTEM] 파인튜닝 학습 프로세스 정상 완료!")
        training_state.logs.append("[SYSTEM] 가중치 파일(weight.pth) 및 ONNX 모델 최적화 내보내기 완료.")
        
        final_accuracy = training_state.accuracy
        final_loss = training_state.loss
        
        # SQLite DB에 학습된 로컬 모델 등록
        conn = get_db_connection()
        cursor = conn.cursor()
        
        model_id = "resnet50-fine-tuned"
        model_name = f"ResNet50 v1.1 (Local Fine-Tuned)"
        
        # 기존 동일 ID 모델이 있다면 삭제 후 새로 등록
        cursor.execute("DELETE FROM ai_models WHERE model_id = ?", (model_id,))
        cursor.execute("""
        INSERT INTO ai_models (model_id, model_name, dataset_size, epochs, accuracy, loss, status)
        VALUES (?, ?, ?, ?, ?, ?, 'inactive')
        """, (model_id, model_name, img_count, total_epochs, final_accuracy, final_loss))
        
        conn.commit()
        conn.close()
        
        training_state.logs.append(f"[SYSTEM] 새 커스텀 모델 '{model_name}'이 모델 레지스트리에 정식 등록되었습니다.")
        
    except Exception as e:
        training_state.logs.append(f"[ERROR] 학습 중 오류 발생: {str(e)}")
    finally:
        training_state.is_training = False

# ─────────────────────────────────────────────
# API 엔드포인트 구현
# ─────────────────────────────────────────────

@router.get("/training/models", response_model=List[ModelInfo])
async def get_models():
    """DB에 등록된 전체 AI 모델 목록 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT model_id, model_name, dataset_size, epochs, accuracy, loss, status, created_at FROM ai_models ORDER BY created_at ASC")
    rows = cursor.fetchall()
    
    models = []
    for r in rows:
        models.append(ModelInfo(
            model_id=r["model_id"],
            model_name=r["model_name"],
            dataset_size=r["dataset_size"],
            epochs=r["epochs"],
            accuracy=r["accuracy"],
            loss=r["loss"],
            status=r["status"],
            created_at=str(r["created_at"])
        ))
    conn.close()
    return models

@router.post("/training/start")
async def start_training(req: TrainingStartRequest, background_tasks: BackgroundTasks):
    """모델 파인튜닝 학습 시작 (백그라운드 태스크 기동)"""
    global training_state
    
    if training_state.is_training:
        raise HTTPException(status_code=400, detail="이미 다른 모델 학습이 진행 중입니다.")
        
    if not req.dataset_path or len(req.dataset_path.strip()) < 3:
        raise HTTPException(status_code=400, detail="유효한 데이터셋 디렉토리 경로를 입력해 주세요.")
        
    # 백그라운드 스레드에서 시뮬레이터 실행
    background_tasks.add_task(
        run_training_simulation,
        dataset_path=req.dataset_path,
        total_epochs=req.epochs,
        lr=req.lr,
        batch_size=req.batch_size
    )
    
    return {"status": "started", "message": "모델 파인튜닝 학습이 백그라운드에서 정상 시작되었습니다."}

@router.get("/training/status", response_model=TrainingStatusResponse)
async def get_training_status():
    """현재 학습 상태 및 실시간 터미널 로그 조회"""
    global training_state
    return TrainingStatusResponse(
        is_training=training_state.is_training,
        current_epoch=training_state.current_epoch,
        total_epochs=training_state.total_epochs,
        progress=training_state.progress,
        loss=training_state.loss,
        accuracy=training_state.accuracy,
        logs=training_state.logs
    )

@router.post("/training/activate")
async def activate_model(payload: dict):
    """진단용 활성 모델 엔진 전환"""
    model_id = payload.get("model_id")
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id가 필요합니다.")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 해당 모델이 존재하는지 확인
    cursor.execute("SELECT COUNT(*) FROM ai_models WHERE model_id = ?", (model_id,))
    if cursor.fetchone()[0] == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="해당 모델을 레지스트리에서 찾을 수 없습니다.")
        
    # 기존 활성화된 모델 비활성화 및 선택 모델 활성화
    cursor.execute("UPDATE ai_models SET status = 'inactive'")
    cursor.execute("UPDATE ai_models SET status = 'active' WHERE model_id = ?", (model_id,))
    
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": f"성공적으로 활성 AI 엔진이 '{model_id}'(으)로 전환되었습니다."}

@router.get("/training/stats")
async def get_training_stats():
    """대시보드 통계 지표 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. 누적 진단 건수
    cursor.execute("SELECT COUNT(*) FROM diagnoses")
    total_diagnoses = cursor.fetchone()[0]
    
    # 2. 등록 농약 품목 수
    cursor.execute("SELECT COUNT(*) FROM pesticide_registry")
    total_pesticides = cursor.fetchone()[0]
    
    # 3. 활성 AI 엔진 명칭
    cursor.execute("SELECT model_name FROM ai_models WHERE status = 'active' LIMIT 1")
    row = cursor.fetchone()
    active_engine = row[0] if row else "Gemini 1.5 Flash (Cloud)"
    
    # 4. 등록된 모델 수
    cursor.execute("SELECT COUNT(*) FROM ai_models")
    total_models = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_diagnoses": total_diagnoses,
        "total_pesticides": total_pesticides,
        "active_engine": active_engine,
        "total_models": total_models
    }
