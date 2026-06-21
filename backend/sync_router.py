"""
농약안전정보시스템 OpenAPI 연동 모듈
- 농약등록정보 API: 수목 관련 등록 농약 전체 목록 수집
- 등록취소 농약정보 API: 취소된 농약을 로컬 DB에서 자동 제거
API 문서: https://api.nongsaro.go.kr
"""

import os
import asyncio
import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from .db import get_db_connection

router = APIRouter()

# ─────────────────────────────────────────────
# 농약안전정보시스템 OpenAPI 엔드포인트
# ─────────────────────────────────────────────
NONGSA_BASE_URL = "http://api.nongsaro.go.kr/service/pestiReg"
NONGSA_CANCEL_URL = "http://api.nongsaro.go.kr/service/pestiCancel"

# 수목 진단에 활용할 주요 수종 키워드 목록
TREE_KEYWORDS = [
    "소나무", "느티나무", "벚나무", "참나무", "잣나무",
    "은행나무", "단풍나무", "메타세쿼이아", "향나무", "밤나무",
    "플라타너스", "이팝나무", "목련", "배롱나무", "회화나무",
    "자작나무", "오동나무", "느릅나무", "오리나무", "수목"
]


class SyncResponse(BaseModel):
    status: str
    message: str
    synchronized_count: int
    cancelled_count: int = 0
    details: Optional[str] = None


# ─────────────────────────────────────────────
# 실제 농약안전정보시스템 API 호출 함수
# ─────────────────────────────────────────────
async def fetch_pesticide_registry(api_key: str, crop_name: str) -> list:
    """농약등록정보 API 호출 - 특정 작물명에 등록된 농약 목록 반환"""
    params = {
        "apiKey": api_key,
        "cropName": crop_name,
        "numOfRows": 100,
        "pageNo": 1,
    }
    results = []
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{NONGSA_BASE_URL}/pestiReg",
                params=params,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    items = (
                        data.get("response", {})
                            .get("body", {})
                            .get("items", {})
                            .get("item", [])
                    )
                    if isinstance(items, dict):
                        items = [items]
                    results = items
        except Exception as e:
            print(f"[NongSa API] 농약등록정보 호출 오류 ({crop_name}): {e}")
    return results


async def fetch_cancelled_pesticides(api_key: str) -> list:
    """등록취소 농약정보 API 호출 - 최근 취소된 농약 목록 반환"""
    params = {
        "apiKey": api_key,
        "numOfRows": 200,
        "pageNo": 1,
    }
    results = []
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{NONGSA_CANCEL_URL}/pestiCancelReg",
                params=params,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    items = (
                        data.get("response", {})
                            .get("body", {})
                            .get("items", {})
                            .get("item", [])
                    )
                    if isinstance(items, dict):
                        items = [items]
                    results = items
        except Exception as e:
            print(f"[NongSa API] 등록취소 농약정보 호출 오류: {e}")
    return results


# ─────────────────────────────────────────────
# 수집 데이터 → 로컬 DB 저장 함수
# ─────────────────────────────────────────────
def _parse_and_upsert_pesticide(cursor, item: dict, crop_name: str) -> bool:
    """
    API 응답 item을 파싱하여 pesticide_registry에 UPSERT.
    신규 삽입 시 True, 중복 시 False 반환.
    """
    # 농약안전정보시스템 응답 필드명 매핑
    product_name = (
        item.get("pestNm") or          # 농약 제품명
        item.get("prdlstNm") or
        item.get("productName") or
        ""
    ).strip()
    active_ingredient = (
        item.get("sickNm") or          # 원제성분명 or 유효성분
        item.get("ingdNm") or
        item.get("activeIngredient") or
        ""
    ).strip()
    dilution_ratio = (
        item.get("usegTime") or        # 희석배수/사용방법
        item.get("dilutionRatio") or
        "라벨 준수"
    ).strip()
    safety_standard = (
        item.get("safetyPrd") or       # 안전사용기준 (수확 전 일수 등)
        item.get("safetyStandard") or
        "라벨 준수"
    ).strip()
    disease_name = (
        item.get("applcPestNm") or     # 적용 병해충명
        item.get("diseaseName") or
        "해충 및 병"
    ).strip()

    if not product_name:
        return False

    # 중복 체크 후 삽입
    cursor.execute(
        "SELECT COUNT(*) FROM pesticide_registry WHERE crop_name=? AND disease_name=? AND product_name=?",
        (crop_name, disease_name, product_name)
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO pesticide_registry
                (crop_name, disease_name, product_name, active_ingredient, dilution_ratio, safety_standard)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (crop_name, disease_name, product_name, active_ingredient, dilution_ratio, safety_standard))
        return True
    return False


def _remove_cancelled_pesticides(cursor, cancelled_items: list) -> int:
    """
    취소 목록에 있는 농약을 로컬 DB에서 삭제.
    삭제된 건수 반환.
    """
    removed = 0
    for item in cancelled_items:
        product_name = (
            item.get("pestNm") or
            item.get("prdlstNm") or
            item.get("productName") or
            ""
        ).strip()
        if product_name:
            cursor.execute(
                "DELETE FROM pesticide_registry WHERE product_name = ?",
                (product_name,)
            )
            removed += cursor.rowcount
    return removed


# ─────────────────────────────────────────────
# 메인 동기화 로직 (async)
# ─────────────────────────────────────────────
async def perform_pesticide_sync_async(reg_api_key: str, cancel_api_key: str):
    """
    1. 수목 키워드별 농약등록정보 API 호출 (reg_api_key) → DB 신규 삽입
    2. 등록취소 농약정보 API 호출 (cancel_api_key) → DB에서 취소 약제 제거
    """
    sync_count = 0
    cancelled_count = 0

    # ① 수종별 등록 농약 수집 (병렬 호출) - 농약등록정보 API 키 사용
    tasks = [fetch_pesticide_registry(reg_api_key, crop) for crop in TREE_KEYWORDS]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    for crop_name, items in zip(TREE_KEYWORDS, all_results):
        if isinstance(items, Exception) or not items:
            continue
        for item in items:
            if _parse_and_upsert_pesticide(cursor, item, crop_name):
                sync_count += 1

    # ② 등록취소 농약 제거 - 등록취소 농약정보 API 키 사용
    cancelled_items = await fetch_cancelled_pesticides(cancel_api_key)
    if cancelled_items:
        cancelled_count = _remove_cancelled_pesticides(cursor, cancelled_items)

    conn.commit()
    conn.close()

    print(f"[NongSa Sync] 신규 등록: {sync_count}건 / 취소 제거: {cancelled_count}건")
    return sync_count, cancelled_count


# ─────────────────────────────────────────────
# 기존 하드코딩 데이터 Fallback (API 실패 시)
# ─────────────────────────────────────────────
def perform_pesticide_sync_fallback():
    """API 호출 실패 시 기본 하드코딩 데이터로 보완"""
    fallback_pesticides = [
        ("소나무", "소나무재선충병", "아바멕틴 액제", "아바멕틴 1.8%",
         "원액 수간주사 (경급 cm당 1ml)", "우화기 전 수간주사, 연 1회"),
        ("소나무", "소나무재선충병", "에마멕틴벤조에이트 유제", "에마멕틴벤조에이트 2.15%",
         "원액 또는 희석 수간주사", "동절기(11월~2월) 수간주사"),
        ("소나무", "소나무잎응애", "밀베멕틴 유제", "밀베멕틴 1.0%",
         "물 20L당 20ml 희석 (1,000배액)", "발생 초엽 수관 살포, 10일 간격 2회 이내"),
        ("벚나무", "갈색무늬구멍병", "티오파네이트메틸 수화물", "티오파네이트메틸 70%",
         "물 20L당 20g 희석 (1,000배액)", "발엽기 가을 전 3회 이내"),
        ("느티나무", "부후", "티오파네이트메틸 도포제", "티오파네이트메틸 3%",
         "도포제 원액 직접 도포", "외과수술 후 환부 도포, 연 1회"),
        ("소나무", "부후", "테부코나졸 수화물", "테부코나졸 25%",
         "물 20L당 10g 희석 (2,000배액) 환부 분무", "외과수술 후 소독 및 살균"),
    ]
    conn = get_db_connection()
    cursor = conn.cursor()
    count = 0
    for row in fallback_pesticides:
        crop, disease, product, ingredient, ratio, safety = row
        cursor.execute(
            "SELECT COUNT(*) FROM pesticide_registry WHERE crop_name=? AND disease_name=? AND product_name=?",
            (crop, disease, product)
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO pesticide_registry
                    (crop_name, disease_name, product_name, active_ingredient, dilution_ratio, safety_standard)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (crop, disease, product, ingredient, ratio, safety))
            count += 1
    conn.commit()
    conn.close()
    return count


# ─────────────────────────────────────────────
# API 라우터
# ─────────────────────────────────────────────
@router.post("/sync/pesticides", response_model=SyncResponse)
async def sync_pesticides():
    # 농약등록정보 API 키 (없으면 취소 API 키를 공유 사용)
    reg_api_key = os.getenv("NONGSA_API_KEY") or os.getenv("NONGSA_CANCEL_API_KEY")
    # 등록취소 농약정보 API 키
    cancel_api_key = os.getenv("NONGSA_CANCEL_API_KEY") or os.getenv("NONGSA_API_KEY")

    if not reg_api_key and not cancel_api_key:
        raise HTTPException(
            status_code=400,
            detail="NONGSA_API_KEY 또는 NONGSA_CANCEL_API_KEY가 .env에 설정되지 않았습니다."
        )

    try:
        sync_count, cancelled_count = await perform_pesticide_sync_async(reg_api_key, cancel_api_key)

        # API에서 가져온 데이터가 없을 경우 Fallback 보완 실행
        if sync_count == 0:
            fallback_count = perform_pesticide_sync_fallback()
            return SyncResponse(
                status="partial",
                message=(
                    f"농약안전정보시스템 API 응답은 수목 해당 데이터 없음 (또는 네트워크 오류). "
                    f"기본 데이터 {fallback_count}건으로 보완 완료. "
                    f"등록취소 제거: {cancelled_count}건"
                ),
                synchronized_count=fallback_count,
                cancelled_count=cancelled_count,
                details="API 호출은 성공했으나 수목 관련 신규 등록 농약 데이터가 없었습니다."
            )

        return SyncResponse(
            status="success",
            message=(
                f"농약안전정보시스템 실시간 동기화 완료! "
                f"신규 등록: {sync_count}건 / 등록취소 제거: {cancelled_count}건"
            ),
            synchronized_count=sync_count,
            cancelled_count=cancelled_count,
        )

    except Exception as e:
        # 전체 실패 시 Fallback 데이터라도 보완
        fallback_count = perform_pesticide_sync_fallback()
        raise HTTPException(
            status_code=500,
            detail=f"동기화 오류: {str(e)}. 기본 데이터 {fallback_count}건으로 보완 완료."
        )


@router.get("/sync/pesticides/status")
async def get_sync_status():
    """현재 로컬 DB에 저장된 농약 데이터 현황 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM pesticide_registry")
    total = cursor.fetchone()["total"]
    cursor.execute("""
        SELECT crop_name, COUNT(*) as cnt
        FROM pesticide_registry
        GROUP BY crop_name
        ORDER BY cnt DESC
    """)
    by_crop = [{"crop": r["crop_name"], "count": r["cnt"]} for r in cursor.fetchall()]
    conn.close()
    return {
        "total_pesticides": total,
        "by_crop": by_crop,
        "nongsa_api_configured": bool(os.getenv("NONGSA_API_KEY"))
    }
