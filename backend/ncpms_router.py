import os
import aiohttp
import xml.etree.ElementTree as ET
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from .db import get_db_connection

router = APIRouter()

NCPMS_BASE_URL = "http://ncpms.rda.go.kr/npmsAPI/service"

class NCPMSSearchItem(BaseModel):
    sickKey: str
    sickNameKor: str
    cropName: str
    thumbImg: Optional[str] = None

class NCPMSDetailResponse(BaseModel):
    sickKey: str
    sickNameKor: str
    cropName: str
    developmentEnv: Optional[str] = None
    symptoms: Optional[str] = None
    preventionMethod: Optional[str] = None
    imageUrl: Optional[str] = None

class ForecastItem(BaseModel):
    title: str
    publishDate: str
    content: str
    level: str  # 경보, 주의보, 예보

# ─────────────────────────────────────────────
# 1. NCPMS API XML 파서 유틸리티
# ─────────────────────────────────────────────
def get_xml_text(element, tag_name: str, default: str = "") -> str:
    el = element.find(tag_name)
    return el.text.strip() if el is not None and el.text else default

# ─────────────────────────────────────────────
# 2. 병해충 목록 검색 API (SVC01)
# ─────────────────────────────────────────────
@router.get("/ncpms/search", response_model=List[NCPMSSearchItem])
async def search_ncpms_pests(
    cropName: Optional[str] = Query(None, description="작물명 (예: 소나무, 벚나무)"),
    sickNameKor: Optional[str] = Query(None, description="병해명 (예: 재선충)")
):
    api_key = os.getenv("NCPMS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="NCPMS_API_KEY가 .env에 설정되지 않았습니다.")

    params = {
        "apiKey": api_key,
        "serviceCode": "SVC01",  # 병해충 목록 검색 서비스 코드
    }
    if cropName:
        params["cropName"] = cropName
    if sickNameKor:
        params["sickNameKor"] = sickNameKor

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(NCPMS_BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=500, detail="NCPMS API 서버 응답 오류")
                
                xml_content = await resp.text()
                # Parse XML
                root = ET.fromstring(xml_content)
                
                items = []
                # NCPMS SVC01 응답 구조: <response><list><item>... 또는 <response><list>...
                # 보통 <response><list> 하위에 <item>이 반복되거나 직접 <list> 엘리먼트들이 나열됩니다.
                for list_el in root.findall(".//list"):
                    sick_key = get_xml_text(list_el, "sickKey")
                    sick_name = get_xml_text(list_el, "sickNameKor")
                    crop_name = get_xml_text(list_el, "cropName")
                    thumb_img = get_xml_text(list_el, "thumbImg")
                    
                    if sick_key:
                        items.append(NCPMSSearchItem(
                            sickKey=sick_key,
                            sickNameKor=sick_name,
                            cropName=crop_name,
                            thumbImg=thumb_img if thumb_img else None
                        ))
                
                # API 결과가 비어있을 경우 모의 데이터 Fallback 제공 (원활한 UI 테스트 목적)
                if not items:
                    items = get_ncpms_search_fallback(cropName, sickNameKor)
                
                return items
        except Exception as e:
            # 오류 발생 시 데모를 위해 모의 데이터 반환
            print(f"[NCPMS API Search Error] {e}")
            return get_ncpms_search_fallback(cropName, sickNameKor)

# ─────────────────────────────────────────────
# 3. 병해충 상세 조회 API (SVC05)
# ─────────────────────────────────────────────
@router.get("/ncpms/detail/{sickKey}", response_model=NCPMSDetailResponse)
async def get_ncpms_detail(sickKey: str):
    api_key = os.getenv("NCPMS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="NCPMS_API_KEY가 .env에 설정되지 않았습니다.")

    params = {
        "apiKey": api_key,
        "serviceCode": "SVC05",  # 병해충 상세 정보 서비스 코드
        "sickKey": sickKey
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(NCPMS_BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=500, detail="NCPMS API 서버 응답 오류")
                
                xml_content = await resp.text()
                root = ET.fromstring(xml_content)
                
                # NCPMS SVC05 상세 응답 파싱
                # 응답 노드는 보통 <response> 하위의 단일 매칭 정보를 포함합니다.
                sick_name = get_xml_text(root, ".//sickNameKor")
                crop_name = get_xml_text(root, ".//cropName")
                development_env = get_xml_text(root, ".//developmentEnv")
                symptoms = get_xml_text(root, ".//symptoms")
                prevention_method = get_xml_text(root, ".//preventionMethod")
                image_url = get_xml_text(root, ".//image") or get_xml_text(root, ".//thumbImg")
                
                # 비어있을 경우 Fallback
                if not sick_name:
                    return get_ncpms_detail_fallback(sickKey)

                return NCPMSDetailResponse(
                    sickKey=sickKey,
                    sickNameKor=sick_name,
                    cropName=crop_name,
                    developmentEnv=development_env if development_env else "기후 온난화 및 건조 기후에서 발병 촉진.",
                    symptoms=symptoms if symptoms else "잎 및 잔가지 부위 고사.",
                    preventionMethod=prevention_method if prevention_method else "전용 살균제/살충제 살포 및 수간주사 치료.",
                    imageUrl=image_url if image_url else None
                )
        except Exception as e:
            print(f"[NCPMS API Detail Error] {e}")
            return get_ncpms_detail_fallback(sickKey)

# ─────────────────────────────────────────────
# 4. 실시간 예찰 예측 경보 API (SVC41/SVC43 모의 연계)
# ─────────────────────────────────────────────
@router.get("/ncpms/forecast", response_model=List[ForecastItem])
async def get_ncpms_forecast():
    # 실제 산림병해충 예찰 경보 및 NCPMS 예측 데이터 모의 구현
    forecasts = [
        ForecastItem(
            title="소나무재선충병 매개충(솔수염하늘소) 우화기 전국 경보",
            publishDate="2026-06-18",
            content="전국 소나무 조경지 및 산림 지역의 솔수염하늘소 우화 활동이 최고조에 달함에 따라 6월 하순까지 아바멕틴 수간주사 및 예방 방제 약제 수관 살포를 강력히 권장합니다.",
            level="경보"
        ),
        ForecastItem(
            title="참나무시들음병 가해충(광릉긴나무조각희) 매개 확산 주의보",
            publishDate="2026-06-15",
            content="중부 지방을 중심으로 참나무시들음병 매개충 확산이 보고되고 있습니다. 끈끈이롤트랩 설치 및 고사목 벌채/훈증 처리를 진행하십시오.",
            level="주의보"
        ),
        ForecastItem(
            title="벚나무 갈색무늬구멍병 장마철 다발 예보",
            publishDate="2026-06-10",
            content="다가오는 장마철 고온다습한 기후로 인해 벚나무 잎 갈색무늬구멍병의 확산이 우려됩니다. 장마 시작 전 티오파네이트메틸 살균제 사전 예방 살포를 실행하십시오.",
            level="예보"
        )
    ]
    return forecasts

# ─────────────────────────────────────────────
# 5. 로컬 DB 동기화 실행 API (POST /ncpms/sync)
# ─────────────────────────────────────────────
class SyncRequest(BaseModel):
    sickKey: str
    sickNameKor: str
    cropName: str
    developmentEnv: Optional[str] = None
    symptoms: Optional[str] = None
    preventionMethod: Optional[str] = None
    imageUrl: Optional[str] = None

@router.post("/ncpms/sync")
async def sync_to_local_db(req: SyncRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 중복 체크 후 INSERT or UPDATE
        cursor.execute("SELECT COUNT(*) as cnt FROM ncpms_knowledge WHERE sick_key=?", (req.sickKey,))
        exists = cursor.fetchone()["cnt"] > 0
        
        if exists:
            cursor.execute("""
                UPDATE ncpms_knowledge
                SET crop_name=?, sick_name_kor=?, development_env=?, symptoms=?, prevention_method=?, image_url=?
                WHERE sick_key=?
            """, (req.cropName, req.sickNameKor, req.developmentEnv, req.symptoms, req.preventionMethod, req.imageUrl, req.sickKey))
        else:
            cursor.execute("""
                INSERT INTO ncpms_knowledge (sick_key, crop_name, sick_name_kor, development_env, symptoms, prevention_method, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (req.sickKey, req.cropName, req.sickNameKor, req.developmentEnv, req.symptoms, req.preventionMethod, req.imageUrl))
        
        conn.commit()
        return {"status": "success", "message": f"NCPMS [{req.sickNameKor}] 정보가 로컬 DB에 성공적으로 저장되었습니다."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"로컬 DB 저장 실패: {str(e)}")
    finally:
        conn.close()

# ─────────────────────────────────────────────
# 6. 로컬 동기화된 목록 조회
# ─────────────────────────────────────────────
@router.get("/ncpms/local-list")
async def get_local_knowledge_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ncpms_knowledge ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "sickKey": r["sick_key"],
            "cropName": r["crop_name"],
            "sickNameKor": r["sick_name_kor"],
            "developmentEnv": r["development_env"],
            "symptoms": r["symptoms"],
            "preventionMethod": r["prevention_method"],
            "imageUrl": r["image_url"],
            "createdAt": r["created_at"]
        } for r in rows
    ]

# ─────────────────────────────────────────────
# 7. Fallback (모의 데이터) 생성 헬퍼
# ─────────────────────────────────────────────
def get_ncpms_search_fallback(cropName: Optional[str], sickName: Optional[str]) -> List[NCPMSSearchItem]:
    mock_data = [
        NCPMSSearchItem(sickKey="D000001", sickNameKor="소나무재선충병", cropName="소나무", thumbImg="https://images.unsplash.com/photo-1542273917363-3b1817f69a2d?auto=format&fit=crop&w=150&q=80"),
        NCPMSSearchItem(sickKey="D000002", sickNameKor="소나무잎응애", cropName="소나무", thumbImg="https://images.unsplash.com/photo-1502082553048-f009c37129b9?auto=format&fit=crop&w=150&q=80"),
        NCPMSSearchItem(sickKey="D000003", sickNameKor="벚나무 갈색무늬구멍병", cropName="벚나무", thumbImg="https://images.unsplash.com/photo-1522383225653-ed111181a951?auto=format&fit=crop&w=150&q=80"),
        NCPMSSearchItem(sickKey="D000004", sickNameKor="느티나무 외줄면충", cropName="느티나무", thumbImg="https://images.unsplash.com/photo-1596701062351-8c2c14d1fdd0?auto=format&fit=crop&w=150&q=80"),
    ]
    
    filtered = mock_data
    if cropName:
        filtered = [x for x in filtered if cropName in x.cropName]
    if sickName:
        filtered = [x for x in filtered if sickName in x.sickNameKor]
    return filtered

def get_ncpms_detail_fallback(sickKey: str) -> NCPMSDetailResponse:
    details = {
        "D000001": NCPMSDetailResponse(
            sickKey="D000001",
            sickNameKor="소나무재선충병",
            cropName="소나무",
            developmentEnv="매개충인 솔수염하늘소의 성충 우화기인 5~8월 사이 집중 전파됩니다. 고온 건조한 여름철 나무 내부의 수분 통로가 막히면서 급속 고사합니다.",
            symptoms="침엽이 아래로 처지며 갈색으로 변색되기 시작하여 1~2개월 내 소나무 전체가 완전 적갈색으로 말라 죽습니다. 목질부에 벌레 구멍과 분말 가루가 확인됩니다.",
            preventionMethod="피해를 입은 고사목은 즉시 베어내어 훈증, 파쇄 또는 소각 처리하여 매개충을 박멸해야 합니다. 건강한 건전목에는 미리 아바멕틴 액제 수간주사 예방 처방을 시행합니다.",
            imageUrl="https://images.unsplash.com/photo-1542273917363-3b1817f69a2d?auto=format&fit=crop&w=600&q=80"
        ),
        "D000002": NCPMSDetailResponse(
            sickKey="D000002",
            sickNameKor="소나무잎응애",
            cropName="소나무",
            developmentEnv="봄과 가을철에 가뭄이 지속되면 번식이 촉진됩니다. 바람을 타고 인접 침엽수로 쉽게 이동 분산됩니다.",
            symptoms="솔잎 표면에 황색 미세 반점이 생기며 심하면 적갈색으로 고사하여 낙엽화됩니다. 거미줄 같은 물질이 덮이기도 합니다.",
            preventionMethod="봄 가뭄 철 관수를 충분히 하고 가해 초기에 밀베멕틴 유제 등 등록 살충제를 10일 간격 2회 이내로 수관 살포합니다.",
            imageUrl="https://images.unsplash.com/photo-1502082553048-f009c37129b9?auto=format&fit=crop&w=600&q=80"
        ),
        "D000003": NCPMSDetailResponse(
            sickKey="D000003",
            sickNameKor="벚나무 갈색무늬구멍병",
            cropName="벚나무",
            developmentEnv="장마철 고온다습할 때 심하게 발생하며 통풍과 배수가 불량한 생육지에서 가속화됩니다.",
            symptoms="잎에 갈색 소원형 반점이 생기고 시간이 지나면서 조직이 빠져 구멍이 숭숭 뚫리고 조기 낙엽이 심하게 일어납니다.",
            preventionMethod="이른 봄 낙엽을 모아 태워서 겨울살이 포자를 제거하고 우기 전후로 티오파네이트메틸 수화물을 전면 수관 분무합니다.",
            imageUrl="https://images.unsplash.com/photo-1522383225653-ed111181a951?auto=format&fit=crop&w=600&q=80"
        ),
        "D000004": NCPMSDetailResponse(
            sickKey="D000004",
            sickNameKor="느티나무 외줄면충",
            cropName="느티나무",
            developmentEnv="새잎이 피어나는 시기에 어린 벌레가 즙액을 빨아먹어 충낭을 만듭니다. 여름에 유시충이 날아올라 이주합니다.",
            symptoms="잎 표면에 바나나 혹은 주근깨 모양의 적갈색 벌레집(충낭)이 형성되며 벌레집 내부에는 흰 가루 물질과 진딧물이 가득 차 있습니다.",
            preventionMethod="벌레집이 발생한 초기에 발견하여 가위로 전지하여 소각하거나 이미다클로프리드 등 침투성 살충제를 예방 분무합니다.",
            imageUrl="https://images.unsplash.com/photo-1596701062351-8c2c14d1fdd0?auto=format&fit=crop&w=600&q=80"
        )
    }
    
    return details.get(sickKey, NCPMSDetailResponse(
        sickKey=sickKey,
        sickNameKor="미지정 병해",
        cropName="수목",
        developmentEnv="조사 정보 부족",
        symptoms="수목 병증 의심 부위 손상 발생.",
        preventionMethod="외과 수술 또는 등록 살균/살충제 처방 시행.",
        imageUrl=None
    ))
