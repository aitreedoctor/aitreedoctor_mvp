import os
import json
import sqlite3
import base64
import tempfile
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from .db import get_db_connection, DB_PATH

def save_base64_to_temp(base64_str: str) -> str:
    if not base64_str:
        return None
    try:
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        img_data = base64.b64decode(base64_str)
        
        # Temp dir
        temp_dir = os.path.join(os.path.dirname(__file__), "static", "temp_photos")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Write to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", dir=temp_dir)
        temp_file.write(img_data)
        temp_file.close()
        return temp_file.name
    except Exception as e:
        print(f"[PDF Service] Error saving base64 to temp: {e}")
        return None

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

router = APIRouter()

# PDF 저장을 위한 디렉토리 설정
PDF_DIR = os.path.join(os.path.dirname(__file__), "static", "pdf")
os.makedirs(PDF_DIR, exist_ok=True)

# Windows 시스템의 맑은 고딕(Malgun Gothic) 폰트 등록
FONT_NAME = "Helvetica"
try:
    font_path = "C:\\Windows\\Fonts\\malgun.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("Malgun", font_path))
        FONT_NAME = "Malgun"
        # 볼드체 등록
        font_path_bold = "C:\\Windows\\Fonts\\malgunbd.ttf"
        if os.path.exists(font_path_bold):
            pdfmetrics.registerFont(TTFont("Malgun-Bold", font_path_bold))
        else:
            pdfmetrics.registerFont(TTFont("Malgun-Bold", font_path))
    else:
        # 시스템에 malgun.ttf가 없는 경우 다른 한글 폰트 탐색
        alternative_fonts = [
            "C:\\Windows\\Fonts\\batang.ttc",
            "C:\\Windows\\Fonts\\gulim.ttc"
        ]
        for alt_path in alternative_fonts:
            if os.path.exists(alt_path):
                pdfmetrics.registerFont(TTFont("Malgun", alt_path))
                FONT_NAME = "Malgun"
                pdfmetrics.registerFont(TTFont("Malgun-Bold", alt_path))
                break
except Exception as e:
    print(f"[PDF Service] 폰트 로드 중 오류 발생, 기본 폰트로 대체합니다: {e}")

class PDFGenerateRequest(BaseModel):
    diagnosis_id: str
    doctor_name: Optional[str] = "홍길동"
    license_number: Optional[str] = "나무의사 제2026-12345호"
    hospital_name: Optional[str] = "아시아나무병원"
    address: Optional[str] = "서울특별시 중구 세종대로 110" # 수목 소재지
    far_photo: Optional[str] = None
    close_photo: Optional[str] = None
    extra_photos: Optional[List[str]] = []

class PDFGenerateResponse(BaseModel):
    status: str
    pdf_url: str
    pdf_path: str

@router.post("/prescriptions/generate", response_model=PDFGenerateResponse)
async def generate_prescription_pdf(req: PDFGenerateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. 진단 정보 가져오기
    cursor.execute("""
    SELECT id, user_id, tree_species, suspected_disease, confidence_score, severity_level, immediate_actions, status_leaves, status_stems, status_roots, treatment_method, pesticide_prescription, created_at
    FROM diagnoses
    WHERE id = ?
    """, (req.diagnosis_id,))
    
    diag = cursor.fetchone()
    if not diag:
        conn.close()
        raise HTTPException(status_code=404, detail="진단 데이터를 찾을 수 없습니다.")
        
    tree_species = diag["tree_species"]
    suspected_disease = diag["suspected_disease"]
    confidence_score = diag["confidence_score"]
    severity_level = diag["severity_level"]
    status_leaves = (diag["status_leaves"] or "정보 없음").replace("\n", "<br/>")
    status_stems = (diag["status_stems"] or "정보 없음").replace("\n", "<br/>")
    status_roots = (diag["status_roots"] or "정보 없음").replace("\n", "<br/>")
    treatment_method = (diag["treatment_method"] or "정보 없음").replace("\n", "<br/>")
    created_at = diag["created_at"]
    
    try:
        immediate_actions = json.loads(diag["immediate_actions"])
    except Exception:
        immediate_actions = []
        
    # 2. 처방 농약 데이터 확보 (진단 레코드 내 저장 데이터 우선 활용)
    pesticides = []
    if diag["pesticide_prescription"]:
        try:
            pesticides = json.loads(diag["pesticide_prescription"])
        except Exception:
            pass
            
    if not pesticides:
        cursor.execute("""
        SELECT product_name, active_ingredient, dilution_ratio, safety_standard
        FROM pesticide_registry
        WHERE ? LIKE '%' || crop_name || '%' AND ? LIKE '%' || disease_name || '%'
        """, (tree_species, suspected_disease))
        
        rows = cursor.fetchall()
        for row in rows:
            dilution = row["dilution_ratio"]
            safety = row["safety_standard"]
            dosage = "수관 살포 시 잎면과 줄기 전체에 골고루 묻도록 살포 (본당 약 5L)"
            prescription_days = "7일"
            if "수간주사" in dilution or "수간주사" in safety:
                dosage = "나무의 크기(DBH)에 따라 주입구당 5ml~10ml씩 수간에 직접 주입"
                prescription_days = "1일 (연 1회)"
            elif "10일" in safety:
                prescription_days = "10일"
            elif "3회" in safety:
                prescription_days = "7일 간격 3회"
            elif "2회" in safety:
                prescription_days = "7일 간격 2회"
                
            pesticides.append({
                "product_name": row["product_name"],
                "active_ingredient": row["active_ingredient"],
                "dilution_ratio": dilution,
                "safety_standard": safety,
                "dosage": dosage,
                "prescription_days": prescription_days
            })
            
    if not pesticides:
        pesticides.append({
            "product_name": "등록 농약 없음",
            "active_ingredient": "해당 수종 및 병해충에 등록된 합법적 약제가 없습니다.",
            "dilution_ratio": "물리적 방제 요망",
            "safety_standard": "지자체 녹지과 및 산림청 방제 가이드라인 준수",
            "dosage": "해당 없음",
            "prescription_days": "해당 없음"
        })
        
    conn.close()
    
    # 3. PDF 빌드 시작
    pdf_filename = f"prescription_{req.diagnosis_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=35,
        bottomMargin=35
    )
    
    styles = getSampleStyleSheet()
    
    # 스타일 커스텀 정의 (한글 지원 및 톤앤매너 매칭)
    title_style = ParagraphStyle(
        name="DocTitle",
        fontName=f"{FONT_NAME}-Bold" if FONT_NAME != "Helvetica" else "Helvetica-Bold",
        fontSize=20,
        leading=26,
        alignment=1, # Center
        textColor=colors.HexColor("#2A5934"), # 딥 그린 메인 테마
        spaceAfter=15
    )
    
    section_style = ParagraphStyle(
        name="SectionTitle",
        fontName=f"{FONT_NAME}-Bold" if FONT_NAME != "Helvetica" else "Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2A5934"),
        spaceBefore=10,
        spaceAfter=5
    )
    
    body_style = ParagraphStyle(
        name="TableBody",
        fontName=FONT_NAME,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#2D3748")
    )
    
    body_bold_style = ParagraphStyle(
        name="TableBodyBold",
        fontName=f"{FONT_NAME}-Bold" if FONT_NAME != "Helvetica" else "Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1A202C")
    )
    
    footer_style = ParagraphStyle(
        name="DocFooter",
        fontName=FONT_NAME,
        fontSize=7.5,
        leading=9,
        alignment=1, # Center
        textColor=colors.HexColor("#A0AEC0"),
        spaceBefore=20
    )
    
    elements = []
    
    # 문서 제목
    elements.append(Paragraph("수목 진단서 및 처방전", title_style))
    elements.append(Spacer(1, 5))
    
    # 1. 기본 정보 테이블
    elements.append(Paragraph("1. 의뢰인 및 소재지 기본 정보", section_style))
    info_data = [
        [Paragraph("진단 번호", body_bold_style), Paragraph(req.diagnosis_id, body_style),
         Paragraph("의뢰인 ID", body_bold_style), Paragraph(diag["user_id"], body_style)],
        [Paragraph("수목 소재지", body_bold_style), Paragraph(req.address or "지정되지 않음", body_style),
         Paragraph("진단 일자", body_bold_style), Paragraph(created_at[:10] if created_at else "즉시", body_style)]
    ]
    info_table = Table(info_data, colWidths=[90, 180, 90, 180])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 1), colors.HexColor("#F7FAFC")),
        ('BACKGROUND', (2, 0), (2, 1), colors.HexColor("#F7FAFC")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))
    
    # 2. 수목 진단서 (수종, 상태, 진단 결과)
    elements.append(Paragraph("2. 수목 진단서 (수종, 수목의 상태 및 진단 결과)", section_style))
    diag_data = [
        [Paragraph("대상 수종", body_bold_style), Paragraph(tree_species, body_style),
         Paragraph("진단 결과 (의심 병해충)", body_bold_style), Paragraph(f"<b>{suspected_disease}</b> ({severity_level}, 정확도: {confidence_score * 100:.1f}%)", body_style)],
        [Paragraph("수목의 상태<br/>(잎)", body_bold_style), Paragraph(status_leaves, body_style),
         Paragraph("수목의 상태<br/>(줄기 및 수간)", body_bold_style), Paragraph(status_stems, body_style)],
        [Paragraph("수목의 상태<br/>(뿌리)", body_bold_style), Paragraph(status_roots, body_style),
         Paragraph("긴급 조치 사항", body_bold_style), Paragraph("<br/>".join([f"• {action}" for action in immediate_actions]) if immediate_actions else "특이사항 없음", body_style)]
    ]
    diag_table = Table(diag_data, colWidths=[90, 180, 90, 180])
    diag_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 2), colors.HexColor("#F7FAFC")),
        ('BACKGROUND', (2, 0), (2, 2), colors.HexColor("#F7FAFC")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(diag_table)
    elements.append(Spacer(1, 10))
    
    # 3. 처방전 (치료방법 및 농약처방)
    elements.append(Paragraph("3. 처방전 (처치 등 치료방법 및 처방 농약 내역)", section_style))
    
    treatment_data = [
        [Paragraph("<b>처치 등 치료방법</b>", body_bold_style), Paragraph(treatment_method, body_style)]
    ]
    treatment_table = Table(treatment_data, colWidths=[110, 430])
    treatment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#F7FAFC")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(treatment_table)
    elements.append(Spacer(1, 6))
    
    pest_headers = [
        Paragraph("농약의 명칭 (상표명 / 성분)", body_bold_style),
        Paragraph("용법 (희석 배수)", body_bold_style),
        Paragraph("용량 (사용량 및 세부 방법)", body_bold_style),
        Paragraph("처방일수 (사용 기간/횟수)", body_bold_style)
    ]
    
    pest_data = [pest_headers]
    for p in pesticides:
        pest_data.append([
            Paragraph(f"<b>{p['product_name']}</b><br/>{p['active_ingredient']}", body_style),
            Paragraph(p["dilution_ratio"], body_style),
            Paragraph(p.get("dosage", "수관 살포"), body_style),
            Paragraph(p.get("prescription_days", "7일"), body_style)
        ])
        
    pest_table = Table(pest_data, colWidths=[150, 130, 160, 100])
    pest_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E6F4EA")), # 처방 헤더 톤앤매너
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(pest_table)
    elements.append(Spacer(1, 20))
    
    # 4. 발행 정보 및 날인
    elements.append(Paragraph("4. 발행자 및 서명 날인", section_style))
    doctor_data = [
        [Paragraph("상호 (나무병원명)", body_bold_style), Paragraph(req.hospital_name or "", body_style),
         Paragraph("나무의사 성명", body_bold_style), Paragraph(f"{req.doctor_name} (서명 또는 직인)", body_bold_style)],
        [Paragraph("면허 자격번호", body_bold_style), Paragraph(req.license_number or "", body_style),
         Paragraph("발행일", body_bold_style), Paragraph(created_at[:10] if created_at else "즉시", body_style)]
    ]
    doctor_table = Table(doctor_data, colWidths=[110, 160, 110, 160])
    doctor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 1), colors.HexColor("#F7FAFC")),
        ('BACKGROUND', (2, 0), (2, 1), colors.HexColor("#F7FAFC")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(doctor_table)
    elements.append(Spacer(1, 10))
    
    # 5. 현장 정밀 사진 증빙
    temp_files = []
    try:
        far_img_path = None
        if req.far_photo:
            far_img_path = save_base64_to_temp(req.far_photo)
            if far_img_path:
                temp_files.append(far_img_path)
                
        close_img_path = None
        if req.close_photo:
            close_img_path = save_base64_to_temp(req.close_photo)
            if close_img_path:
                temp_files.append(close_img_path)
                
        extra_img_paths = []
        if req.extra_photos:
            for extra_b64 in req.extra_photos:
                if extra_b64:
                    path = save_base64_to_temp(extra_b64)
                    if path:
                        extra_img_paths.append(path)
                        temp_files.append(path)
                        
        if far_img_path or close_img_path or extra_img_paths:
            from reportlab.platypus import PageBreak
            elements.append(PageBreak())  # 항상 새로운 페이지(첨부 전용 페이지)에서 시작하도록 강제 넘김
            elements.append(Paragraph("5. 현장 정밀 사진 증빙", section_style))
            
            from reportlab.platypus import Image
            
            # Left: Far Photo (원경)
            far_photo_flowable = None
            if far_img_path:
                try:
                    far_photo_flowable = Image(far_img_path, width=230, height=160)
                except Exception as e:
                    print(f"Error creating far photo Image: {e}")
                    far_photo_flowable = Paragraph("원경 이미지 생성 에러", body_style)
            else:
                far_photo_flowable = Paragraph("등록된 원경 사진이 없습니다.", body_style)
                
            # Right: Close Photo (근경)
            close_photo_flowable = None
            if close_img_path:
                try:
                    close_photo_flowable = Image(close_img_path, width=230, height=160)
                except Exception as e:
                    print(f"Error creating close photo Image: {e}")
                    close_photo_flowable = Paragraph("근경 이미지 생성 에러", body_style)
            else:
                close_photo_flowable = Paragraph("등록된 근경 사진이 없습니다.", body_style)
                
            photo_table_data = [
                [Paragraph("<b>[원경 사진 - 전체 수형]</b>", body_style), Paragraph("<b>[근경 사진 - 병증 부위 상세]</b>", body_style)],
                [far_photo_flowable, close_photo_flowable]
            ]
            
            photo_table_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]
            
            if extra_img_paths:
                extra_flowables = []
                for path in extra_img_paths:
                    try:
                        extra_flowables.append(Image(path, width=140, height=100))
                    except Exception as e:
                        print(f"Error creating extra photo Image: {e}")
                
                # Append a row for extra photos
                photo_table_data.append([Paragraph("<b>[추가 현장 사진 증빙]</b>", body_style), ""])
                
                # 내부 테이블을 사용해 가로로 배치
                if extra_flowables:
                    from reportlab.platypus import Table as InnerTable, TableStyle as InnerTableStyle
                    inner_table = InnerTable([extra_flowables])
                    inner_table.setStyle(InnerTableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        ('TOPPADDING', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ]))
                    photo_table_data.append([inner_table, ""])
                else:
                    photo_table_data.append(["", ""])
                    
                photo_table_styles.append(('SPAN', (0, 2), (1, 2)))
                photo_table_styles.append(('SPAN', (0, 3), (1, 3)))
            
            photo_table = Table(photo_table_data, colWidths=[250, 250])
            photo_table.setStyle(TableStyle(photo_table_styles))
            elements.append(photo_table)
            elements.append(Spacer(1, 10))
    except Exception as e:
        print(f"Error drawing photos section: {e}")
        
    # 하단 확인 문구
    elements.append(Paragraph("위와 같이 「산림보호법」 및 「농약관리법」 규정에 의하여 수목 진단 및 처방 결과를 발행합니다.", ParagraphStyle(
        name="Affiliation",
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        alignment=1,
        spaceBefore=25,
        textColor=colors.HexColor("#2D3748")
    )))
    
    # 푸터
    elements.append(Paragraph("AITreeDoctor AI 기반 수목 정밀 처방전 자동 발급 솔루션", footer_style))
    
    # 빌드 실행
    try:
        doc.build(elements)
    finally:
        # Clean up temporary image files
        for path in temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"[PDF Service] Error removing temp file {path}: {e}")
    
    # PDF URL 반환 (FastAPI static 경로)
    pdf_url = f"/static/pdf/{pdf_filename}"
    
    # diagnoses 테이블에 pdf_url 컬럼 업데이트
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE diagnoses
    SET pdf_url = ?
    WHERE id = ?
    """, (pdf_url, req.diagnosis_id))
    conn.commit()
    conn.close()
    
    return PDFGenerateResponse(
        status="success",
        pdf_url=pdf_url,
        pdf_path=pdf_path
    )
