// AITreeDoctor Frontend Logic

// 전역 상태 관리
let selectedFarFile = null;
let selectedCloseFile = null;
let currentDiagnosisId = null;
let selectedFarBase64 = null; // 원경 수목 사진 Base64 데이터
let selectedCloseBase64 = null; // 근경 수목 사진 Base64 데이터
let extraPhotos = []; // 추가 현장 사진 Base64 데이터 배열 (최대 3장)
const BACKEND_URL = window.location.origin;


// 기본 설정 값
let appSettings = {
    hospitalName: "아시아나무병원",
    licenseNumber: "나무의사 제2026-12345호",
    doctorName: "홍길동",
    hospitalAddress: "서울특별시 서초구 서초대로 123",
    userRole: "general" // 기본값을 일반 이용자로 설정
};

// 1. 초기 로드
document.addEventListener("DOMContentLoaded", () => {
    loadSettings();
    initUploadZone();
    loadHistoryTable();
    
    // 2.5초 뒤 스플래시 화면 숨김 및 메인 앱 쉘 오픈
    setTimeout(() => {
        const splash = document.getElementById("screen-splash");
        const shell = document.getElementById("app-shell");
        if (splash && shell) {
            splash.classList.add("hidden");
            shell.classList.remove("hidden");
        }
    }, 2500);
});



// 2. 설정 관련 기능
function loadSettings() {
    const saved = localStorage.getItem("aitreedoctor_mvp_settings");
    if (saved) {
        try {
            appSettings = JSON.parse(saved);
        } catch (e) {
            console.error("설정 로드 실패", e);
        }
    }
    
    // UI에 바인딩
    const sbHospital = document.getElementById("sb-hospital-name");
    const sbDoctor = document.getElementById("sb-doctor-name");
    if (sbHospital) sbHospital.innerText = appSettings.hospitalName;
    if (sbDoctor) sbDoctor.innerText = appSettings.doctorName + " 나무의사";

    
    const hNameInput = document.getElementById("setting-hospital-name");
    const licInput = document.getElementById("setting-license-number");
    const docInput = document.getElementById("setting-doctor-name");
    const addrInput = document.getElementById("setting-hospital-address");
    const roleInput = document.getElementById("setting-user-role");
    
    if (hNameInput) hNameInput.value = appSettings.hospitalName;
    if (licInput) licInput.value = appSettings.licenseNumber;
    if (docInput) docInput.value = appSettings.doctorName;
    if (addrInput) addrInput.value = appSettings.hospitalAddress;
    if (roleInput) roleInput.value = appSettings.userRole || "general";
    
    toggleRoleUI();
}

function saveSettings() {
    appSettings.hospitalName = document.getElementById("setting-hospital-name").value;
    appSettings.licenseNumber = document.getElementById("setting-license-number").value;
    appSettings.doctorName = document.getElementById("setting-doctor-name").value;
    appSettings.hospitalAddress = document.getElementById("setting-hospital-address").value;
    appSettings.userRole = document.getElementById("setting-user-role").value;
    
    localStorage.setItem("aitreedoctor_mvp_settings", JSON.stringify(appSettings));
    loadSettings();
    
    alert("설정 정보가 성공적으로 저장되었습니다!");
}

function toggleRoleUI() {
    const role = document.getElementById("setting-user-role") ? document.getElementById("setting-user-role").value : (appSettings.userRole || "general");
    
    // 일반 이용자일 때는 병원 관련 면허증 입력 폼 필드들을 숨김
    const fields = [
        "setting-hospital-name",
        "setting-license-number",
        "setting-doctor-name",
        "setting-hospital-address"
    ];
    
    fields.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            const parent = el.closest(".form-group");
            if (role === "general") {
                if (parent) parent.style.display = "none";
            } else {
                if (parent) parent.style.display = "block";
            }
        }
    });

    // 시스템 어드민 바로가기도 나무의사 회원 이상일 경우에만 노출
    const adminGateway = document.querySelector(".settings-admin-gateway");
    if (adminGateway) {
        if (role === "doctor") {
            adminGateway.style.display = "block";
        } else {
            adminGateway.style.display = "none";
        }
    }
}

// 3. 섹션 전환 (하단 탭 바 메뉴 클릭)
function switchSection(sectionId) {
    // 1. 모든 탭 숨기기
    document.querySelectorAll(".tab-content").forEach(tab => {
        tab.classList.remove("active");
        tab.classList.add("hidden");
    });
    
    // 2. 대상 탭 활성화
    const targetTab = document.getElementById(sectionId);
    if (targetTab) {
        targetTab.classList.remove("hidden");
        targetTab.classList.add("active");
    }
    
    // 3. 하단 내비게이션 바 아이템 활성화 상태 업데이트
    document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.remove("active");
    });
    
    const clickedItem = Array.from(document.querySelectorAll(".nav-item")).find(item => 
        item.getAttribute("onclick").includes(sectionId)
    );
    if (clickedItem) clickedItem.classList.add("active");
    
    // 4. 타이틀 업데이트 및 특정 탭 로딩 액션
    const titleEl = document.querySelector(".header-title");
    if (titleEl) {
        if (sectionId === "tab-diagnose") {
            titleEl.innerText = "AITreeDoctor";
        } else if (sectionId === "tab-history") {
            titleEl.innerText = "진단 이력";
            loadHistoryTable();
        } else if (sectionId === "tab-settings") {
            titleEl.innerText = "의사 설정";
        }
    }
}


// 4. 이미지 업로드 드롭존 구현
function initUploadZone() {
    setupSingleUploadZone("far");
    setupSingleUploadZone("close");
}

function setupSingleUploadZone(type) {
    const uploadZone = document.getElementById(`upload-zone-${type}`);
    const fileInput = document.getElementById(`file-input-${type}`);
    const removeBtn = document.getElementById(`btn-remove-img-${type}`);
    
    if (!uploadZone || !fileInput || !removeBtn) return;
    
    uploadZone.addEventListener("click", (e) => {
        if (e.target !== removeBtn && !removeBtn.contains(e.target)) {
            fileInput.click();
        }
    });
    
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleFileSelect(fileInput.files[0], type);
        }
    });
    
    uploadZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = "var(--primary)";
    });
    
    uploadZone.addEventListener("dragleave", () => {
        uploadZone.style.borderColor = "var(--border)";
    });
    
    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = "var(--border)";
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0], type);
        }
    });
    
    removeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (type === "far") {
            selectedFarFile = null;
            selectedFarBase64 = null;
        } else {
            selectedCloseFile = null;
            selectedCloseBase64 = null;
        }
        fileInput.value = "";
        document.getElementById(`upload-preview-${type}`).classList.add("hidden");
        document.getElementById(`upload-placeholder-${type}`).classList.remove("hidden");
        
        // 스캐너 배경 이미지 디폴트로 초기화
        const scannerBg = document.getElementById(`scanner-bg-${type}`);
        if (scannerBg) {
            scannerBg.src = type === "far" ? "bg_far_view.png" : "bg_close_view.png";
        }
        
        // 결과 영역 및 대장 입력 폼 숨김 (둘 중 하나가 지워지면 진단 해제)
        document.getElementById("results-container").classList.add("hidden");
        document.getElementById("report-form-card").classList.add("hidden");
        
        // 추가 사진 영역 숨김 및 데이터 초기화
        const extraSection = document.getElementById("additional-photos-section");
        if (extraSection) extraSection.classList.add("hidden");
        clearExtraPhotos();
        
        // 상태 텍스트 업데이트
        const statusText = document.getElementById("scanner-status-text");
        if (statusText) {
            if (selectedFarFile) {
                statusText.innerHTML = `<i class="fa-solid fa-circle-info"></i> 원경 사진이 등록되었습니다. <strong>근경 사진(환부 상세)</strong>을 추가로 등록해 주세요.`;
            } else if (selectedCloseFile) {
                statusText.innerHTML = `<i class="fa-solid fa-circle-info"></i> 근경 사진이 등록되었습니다. <strong>원경 사진(전체 수형)</strong>을 추가로 등록해 주세요.`;
            } else {
                statusText.innerHTML = `<i class="fa-solid fa-circle-info"></i> 원경과 근경 사진 2장을 모두 등록하면 실시간 AI 스캔이 자동 가동됩니다.`;
            }
        }
    });
}

function handleFileSelect(file, type) {
    // 신규 스캔 대상이 업로드되면 이전 추가 사진 목록을 초기화합니다.
    clearExtraPhotos();

    if (type === "far") {
        selectedFarFile = file;
    } else {
        selectedCloseFile = file;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            // 이미지 압축 및 리사이징 (최대 800px)
            const canvas = document.createElement("canvas");
            let width = img.width;
            let height = img.height;
            const maxDim = 800;
            
            if (width > maxDim || height > maxDim) {
                if (width > height) {
                    height = Math.round((height * maxDim) / width);
                    width = maxDim;
                } else {
                    width = Math.round((width * maxDim) / height);
                    height = maxDim;
                }
            }
            
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(img, 0, 0, width, height);
            
            const compressedBase64 = canvas.toDataURL("image/jpeg", 0.75);
            if (type === "far") {
                selectedFarBase64 = compressedBase64;
            } else {
                selectedCloseBase64 = compressedBase64;
            }
            
            document.getElementById(`preview-img-${type}`).src = compressedBase64;
            document.getElementById(`upload-placeholder-${type}`).classList.add("hidden");
            document.getElementById(`upload-preview-${type}`).classList.remove("hidden");
            
            // 우측 스캐너의 배경에도 압축된 사진 데이터 반영
            const scannerBg = document.getElementById(`scanner-bg-${type}`);
            if (scannerBg) {
                scannerBg.src = compressedBase64;
            }
            
            // 원경 사진 분석 시에만 파일명 참고하여 기본 수종 선택
            if (type === "far") {
                const filename = file.name.toLowerCase();
                const treeSpeciesInput = document.getElementById("tree-species-input");
                if (filename.includes("벚") || filename.includes("cherry")) {
                    treeSpeciesInput.value = "벚나무";
                } else if (filename.includes("느티") || filename.includes("elm")) {
                    treeSpeciesInput.value = "느티나무";
                } else {
                    treeSpeciesInput.value = "소나무"; // 기본값
                }
            }
            
            // 두 사진이 모두 등록된 경우 자동으로 스캔 및 AI 진단 가동
            if (selectedFarFile && selectedCloseFile) {
                const statusText = document.getElementById("scanner-status-text");
                if (statusText) {
                    statusText.innerHTML = `<i class="fa-solid fa-circle-info"></i> 원경 사진과 근경 사진(환부 상세)이 등록되었습니다. 환경과 환부사진을 추가로 등록해 주세요.`;
                }
                triggerAutoScan();
            } else {
                const statusText = document.getElementById("scanner-status-text");
                if (statusText) {
                    if (type === "far") {
                        statusText.innerHTML = `<i class="fa-solid fa-circle-info"></i> 원경 사진이 등록되었습니다. <strong>근경 사진(환부 상세)</strong>을 추가로 등록해 주세요.`;
                    } else {
                        statusText.innerHTML = `<i class="fa-solid fa-circle-info"></i> 근경 사진이 등록되었습니다. <strong>원경 사진(전체 수형)</strong>을 추가로 등록해 주세요.`;
                    }
                }
            }
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}



// 5. GPS 위치 정보 획득 및 Nominatim 주소 변환
function requestGPS() {
    const banner = document.getElementById("location-status-banner");
    const statusText = document.getElementById("location-status-text");
    
    banner.classList.remove("hidden");
    statusText.innerText = "GPS 신호를 수집하고 있습니다...";
    
    if (!navigator.geolocation) {
        statusText.innerText = "이 브라우저는 GPS 수집을 지원하지 않습니다.";
        return;
    }
    
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;
            
            // HUD 변수 업데이트
            document.getElementById("hud-lat").innerText = lat.toFixed(4);
            document.getElementById("hud-lng").innerText = lng.toFixed(4);
            
            statusText.innerText = `GPS 수집 성공 (${lat.toFixed(4)}, ${lng.toFixed(4)}). 한글 주소 변환 중...`;
            
            // Nominatim 역지오코딩 호출 (한글 주소 강제)
            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&accept-language=ko`)
                .then(res => res.json())
                .then(data => {
                    if (data && data.address) {
                        const addr = data.address;
                        
                        // 한국식 주소 조립 알고리즘
                        let city = addr.province || addr.city || addr.state || "";
                        let borough = addr.borough || addr.district || addr.suburb || "";
                        let road = addr.road || "";
                        let house_number = addr.house_number || "";
                        let building = addr.building || addr.amenity || "";
                        
                        let cleanAddr = `${city} ${borough} ${road} ${house_number}`.trim().replace(/\s+/g, ' ');
                        
                        if (building) {
                            cleanAddr += ` (${building})`;
                        }
                        
                        if (!cleanAddr || cleanAddr.length < 5) {
                            // 역순 파싱 복구
                            if (data.display_name) {
                                const parts = data.display_name.split(",").map(p => p.trim());
                                // 대한민국, 우편번호 제거 후 한글 주소 조합
                                const filtered = parts.reverse().filter(p => p !== "대한민국" && !/^\d{3}-\d{3}$/.test(p) && !/^\d{5}$/.test(p));
                                cleanAddr = filtered.join(" ");
                            }
                        }
                        
                        document.getElementById("address-input").value = cleanAddr;
                        statusText.innerText = "GPS 도로명 한글 주소 자동 변환 완료!";
                    } else {
                        fallbackAddress();
                    }
                })
                .catch(err => {
                    console.error("역지오코딩 에러", err);
                    fallbackAddress();
                });
        },
        (err) => {
            console.warn("GPS 권한 거부 또는 실패. Fallback 적용", err);
            fallbackAddress();
        },
        { timeout: 8000 }
    );
}

function fallbackAddress() {
    // 권한 오류 또는 보안(HTTPS 미사용) 시 광명시청 디폴트 Fallback
    document.getElementById("address-input").value = "경기도 광명시 시청로 20 (광명시청)";
    document.getElementById("location-status-text").innerText = "보안 환경상 GPS 수집 불가로 모의 국문 주소(광명시청)를 대입했습니다.";
    document.getElementById("hud-lat").innerText = "37.4782";
    document.getElementById("hud-lng").innerText = "126.8643";
}

// 6. 카카오 주소 검색 기능 통합
function searchAddressWithKakao() {
    new daum.Postcode({
        oncomplete: function(data) {
            let fullAddress = data.roadAddress; // 도로명 주소
            let extraAddress = ''; 

            if (data.bname !== '' && /[동|로|가]$/g.test(data.bname)) {
                extraAddress += data.bname;
            }
            if (data.buildingName !== '' && data.apartment === 'Y') {
                extraAddress += (extraAddress !== '' ? ', ' + data.buildingName : data.buildingName);
            }
            if (extraAddress !== '') {
                extraAddress = ' (' + extraAddress + ')';
            }

            const finalAddr = fullAddress + extraAddress;
            document.getElementById("address-input").value = finalAddr;
            
            const banner = document.getElementById("location-status-banner");
            const statusText = document.getElementById("location-status-text");
            banner.classList.remove("hidden");
            statusText.innerText = "카카오 우편번호 주소 검색 입력 완료!";
        }
    }).open();
}

// 7. AI 정밀 진단 버튼 핸들러 및 스캔 시뮬레이션
// 7. 실시간 AI 수목 스캔 시뮬레이션
function triggerAutoScan() {
    // 1. UI 스캐너 모드로 전환 및 HUD 렌더
    const scannerContainer = document.getElementById("scanner-container");
    const resultsContainer = document.getElementById("results-container");
    const hudLayer = document.getElementById("hud-layer");
    const scanOverlay = document.getElementById("scan-overlay-message");
    
    resultsContainer.classList.add("hidden");
    scannerContainer.classList.remove("idle");
    hudLayer.classList.remove("hidden");
    scanOverlay.classList.remove("hidden");
    
    // 이전 진단서 상세 폼 숨김
    document.getElementById("report-form-card").classList.add("hidden");
    
    // HUD 난수 변화 시뮬레이션
    const hudInterval = setInterval(() => {
        document.getElementById("hud-temp").innerText = (20 + Math.random() * 8).toFixed(1) + "°C";
        document.getElementById("hud-humid").innerText = Math.round(50 + Math.random() * 15) + "%";
        document.getElementById("hud-chl").innerText = (65 + Math.random() * 20).toFixed(1);
    }, 300);
    
    // 프로그레스 바 시뮬레이션 (2초간 순차 가동)
    const progressTitle = document.getElementById("scan-progress-title");
    const progressDesc = document.getElementById("scan-progress-desc");
    const progressBarFill = document.getElementById("progress-bar-fill");
    
    let pct = 0;
    progressBarFill.style.width = "0%";
    const progressInterval = setInterval(() => {
        pct += 10;
        progressBarFill.style.width = pct + "%";
        
        if (pct === 20) {
            progressTitle.innerText = "1단계: 수목 스펙트럼 분석 중...";
            progressDesc.innerText = "원격 센싱을 통해 고사엽 비율을 측정하고 있습니다.";
        } else if (pct === 50) {
            progressTitle.innerText = "2단계: 엽록소 반사율 연산 중...";
            progressDesc.innerText = "수분 흡수 반사 패턴 분석으로 쇠퇴도를 연산합니다.";
        } else if (pct === 80) {
            progressTitle.innerText = "3단계: 수간 바이오 데이터 분석 중...";
            progressDesc.innerText = "병해충 패턴 매칭 및 대한민국 농약관리법 교차 검증 중...";
        }
        
        if (pct >= 100) {
            clearInterval(progressInterval);
            clearInterval(hudInterval);
            executeAPIRequest();
        }
    }, 200);
}


// 8. 백엔드 API 연동 (CORS 및 예외시 가상 폴백 처리)
function executeAPIRequest() {
    const address = document.getElementById("address-input").value || "소재지 미지정";
    const user_id = appSettings.doctorName;
    
    const formData = new FormData();
    formData.append("far_file", selectedFarFile);
    formData.append("close_file", selectedCloseFile);
    formData.append("user_id", user_id);
    formData.append("address", address);
    
    if (extraPhotos && extraPhotos.length > 0) {
        formData.append("extra_photos_base64", JSON.stringify(extraPhotos));
    }
    
    fetch(`${BACKEND_URL}/api/v1/diagnose`, {
        method: "POST",
        body: formData
    })
    .then(res => {
        if (!res.ok) throw new Error("서버 에러");
        return res.json();
    })
    .then(data => {
        renderDiagnosisResult(data);
    })
    .catch(err => {
        console.warn("[Backend Offline] 로컬 백엔드 연결 불가. 웹 데모 가상 폴백 데이터 구동합니다.", err);
        // 오프라인 가상 폴백 데이터 (Gemini mock 대체)
        const filename = selectedFarFile.name + "_" + selectedCloseFile.name;
        const fallbackData = simulateMockDiagnosis(filename, address);
        renderDiagnosisResult(fallbackData);
    });
}

function simulateMockDiagnosis(filename, address) {
    const fname = filename.toLowerCase();
    let result = {
        id: "offline-" + Math.random().toString(36).substr(2, 9),
        tree_species: "소나무",
        suspected_disease: "소나무재선충병",
        confidence_score: 0.94,
        severity_level: "심각",
        status_leaves: "침엽의 적갈색 괴사화(Necrosis)가 급격히 진행되며 수관 상부에서 하단부로 확산 및 탈엽(Abscission) 관찰됨.",
        status_stems: "수간(Trunk) 부위 매개충 침입 흔적인 우화공(Exit holes) 및 수지(Resin) 분비 저하, 목질부 쇠퇴 진행됨.",
        status_roots: "근원부 토양 답압(Soil compaction)으로 인한 세근(Fine roots) 발달 장해 및 수분 스트레스 동반 추정.",
        treatment_method: "[화학적 방제] 매개충 우화기 이전 예방적 차원의 아바멕틴(Abamectin) 수간주사(Trunk injection) 주입 요망.\n[임업적/물리적 방제] 감염 우려목 및 고사목은 산림보호법에 의거 즉시 벌채 후 훈증(Fumigation), 파쇄, 또는 소각 처리하여 전염원을 원천 차단해야 함.",
        status_leaves_summary: "솔잎 전체가 갈색 괴사화되며 급격히 마르고 있음.",
        status_stems_summary: "수간에 매개충 우화공 흔적이 관찰되며 송진 분비가 멈춤.",
        status_roots_summary: "토양 답압 및 가뭄으로 인해 수분/영양 흡수 기능이 쇠퇴함.",
        treatment_method_summary: "감염목은 즉시 벌채 소각 처리하고 인근 나무에 예방 수간주사 처방.",
        immediate_actions: [
            "피해 고사목 발견 즉시 관계 기관(산림청/지자체 녹지과) 신고",
            "감염 우려 수목은 즉시 벌채 후 훈증 또는 소각 처리",
            "주변 건전목에 예방 목적으로 아바멕틴 수간주사 처방 실시"
        ],
        pesticides: [
            {
                product_name: "아바멕틴 액제",
                active_ingredient: "아바멕틴 1.8%",
                dilution_ratio: "원액 수간주사 (경급 cm당 1ml)",
                safety_standard: "우화기 전 수간주사, 연 1회"
            },
            {
                product_name: "에마멕틴벤조에이트 유제",
                active_ingredient: "에마멕틴벤조에이트 2.15%",
                dilution_ratio: "원액 또는 희석 수간주사",
                safety_standard: "동절기(11월~2월) 수간주사"
            }
        ],
        address: address
    };
    
    if (fname.includes("응애") || fname.includes("mite")) {
        result.suspected_disease = "소나무잎응애";
        result.confidence_score = 0.88;
        result.severity_level = "보통";
        result.status_leaves_summary = "솔잎이 누렇게 변색되고 점차 떨어짐.";
        result.status_stems_summary = "잎 표면 오염으로 나무가 약해짐.";
        result.status_roots_summary = "봄 가뭄으로 수분 부족 상태.";
        result.treatment_method_summary = "응애약을 전체적으로 뿌리고 물을 충분히 줌.";
        result.immediate_actions = [
            "피해엽 및 하엽 고사 상태 모니터링",
            "봄철 가뭄기 수분 공급 및 정기적 관수 요망",
            "전용 등록 밀베멕틴 응애약제 수관 살포 실시"
        ];
        result.pesticides = [
            {
                product_name: "밀베멕틴 유제",
                active_ingredient: "밀베멕틴 1.0%",
                dilution_ratio: "물 20L당 20ml 희석 (1,000배액)",
                safety_standard: "발생 초엽 수관 살포, 10일 간격 2회 이내"
            }
        ];
    } else if (fname.includes("벚") || fname.includes("cherry") || fname.includes("구멍")) {
        result.tree_species = "벚나무";
        result.suspected_disease = "갈색무늬구멍병";
        result.confidence_score = 0.85;
        result.severity_level = "경미";
        result.status_leaves_summary = "잎에 갈색 반점이 생기고 구멍이 뚫림.";
        result.status_stems_summary = "가지 성장에 약간의 영향이 예상됨.";
        result.status_roots_summary = "뿌리 주변 통풍이 잘 안 됨.";
        result.treatment_method_summary = "떨어진 병든 잎을 태우고 봄에 살균제 예방 접종.";
        result.immediate_actions = [
            "낙엽 및 낙지 즉시 수거 후 소각하여 월동 전염원 차단",
            "봄철 발엽기 이후 등록 살균제 예방 수관 살포 진행"
        ];
        result.pesticides = [
            {
                product_name: "티오파네이트메틸 수화물",
                active_ingredient: "티오파네이트메틸 70%",
                dilution_ratio: "물 20L당 20g 희석 (1,000배액)",
                safety_standard: "발엽기 가을 전 3회 이내"
            }
        ];
    }
    
    return result;
}

function formatTreatmentMethod(text) {
    if (!text) return "해당 사항 없음";
    
    // Split text by brackets [Category]
    const pattern = /(\[[^\]]+\])/g;
    const parts = text.split(pattern);
    
    if (parts.length <= 1) {
        return text.replace(/\n/g, "<br/>");
    }
    
    let html = "";
    let currentTitle = "";
    
    for (let i = 0; i < parts.length; i++) {
        const part = parts[i].trim();
        if (!part) continue;
        
        if (part.startsWith("[") && part.endsWith("]")) {
            currentTitle = part.slice(1, -1);
        } else {
            let desc = part.replace(/^[:\s\-•]+/, "").trim();
            // Split into sentences
            const sentences = desc.split(/\.(?:\s+|$)/);
            let formattedDesc = "";
            sentences.forEach(s => {
                let cleanS = s.trim().replace(/^[:\s\-•]+/, "").trim();
                if (cleanS) {
                    formattedDesc += `<li style="margin-bottom: 6px; line-height: 1.5; list-style-type: disc;">${cleanS}.</li>`;
                }
            });
            
            if (formattedDesc) {
                formattedDesc = `<ul style="margin: 6px 0 0 0; padding-left: 20px; color: var(--text-main); font-weight: 500;">${formattedDesc}</ul>`;
            } else {
                formattedDesc = `<p style="margin: 6px 0 0 0; color: var(--text-main); font-weight: 500;">${desc}</p>`;
            }
            
            html += `
                <div class="treatment-group" style="margin-bottom: 16px;">
                    <div class="treatment-group-title" style="margin-bottom: 4px;">
                        <span style="background-color: var(--accent-light); color: var(--accent); padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; display: inline-block;">${currentTitle}</span>
                    </div>
                    ${formattedDesc}
                </div>
            `;
            currentTitle = "";
        }
    }
    return html;
}

// 9. 진단 결과 렌더링 및 로컬스토리지 대장 저장
function renderDiagnosisResult(data) {
    // 스캔 오버레이 닫기
    document.getElementById("hud-layer").classList.add("hidden");
    document.getElementById("scan-overlay-message").classList.add("hidden");
    document.getElementById("scanner-container").classList.add("idle");
    
    // 결과 화면 노출
    document.getElementById("results-container").classList.remove("hidden");
    
    // 좌측 상세 정보 입력 폼 활성화 및 데이터 대입 (나무의사 회원 이상일 경우에만 노출)
    const reportForm = document.getElementById("report-form-card");
    if (appSettings.userRole === "doctor") {
        reportForm.classList.remove("hidden");
    } else {
        reportForm.classList.add("hidden");
    }
    document.getElementById("tree-species-input").value = data.tree_species;
    
    // 추가 사진 구역 활성화
    const extraSection = document.getElementById("additional-photos-section");
    if (extraSection) {
        extraSection.classList.remove("hidden");
    }
    // (이전 진단 기록의 추가 사진 지우기는 handleFileSelect에서 신규 업로드 시에만 수행하도록 변경)
    
    // 데이터 매핑
    const sevBadge = document.getElementById("res-severity");
    sevBadge.innerText = data.severity_level;
    sevBadge.className = `badge-severity severity-${data.severity_level}`;
    
    document.getElementById("res-disease").innerText = `${data.tree_species} - ${data.suspected_disease}`;
    document.getElementById("res-confidence").innerText = `${Math.round(data.confidence_score * 100)}%`;
    
    // 법정 진단 잎/줄기/뿌리 상태 바인딩 (모바일 UI는 요약본 노출)
    document.getElementById("res-status-leaves").innerText = data.status_leaves_summary || data.status_leaves || "양호함";
    document.getElementById("res-status-stems").innerText = data.status_stems_summary || data.status_stems || "양호함";
    document.getElementById("res-status-roots").innerText = data.status_roots_summary || data.status_roots || "양호함";
    
    // 처치 등 치료방법 바인딩 (가독성 개선 적용)
    document.getElementById("res-treatment-method").innerHTML = formatTreatmentMethod(data.treatment_method);
    
    // 즉각 조치 렌더링
    const actionsList = document.getElementById("res-actions-list");
    actionsList.innerHTML = "";
    data.immediate_actions.forEach(act => {
        const li = document.createElement("li");
        li.innerText = act;
        actionsList.appendChild(li);
    });
    
    // 등록 농약 매핑 (명칭, 용법, 용량, 처방일수)
    const tbody = document.getElementById("res-pesticide-tbody");
    tbody.innerHTML = "";
    data.pesticides.forEach(p => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${p.product_name}</strong><br/><span style="font-size: 9px; color: var(--text-muted);">${p.active_ingredient}</span></td>
            <td>${p.dilution_ratio}</td>
            <td>${p.dosage || "수관 살포"}</td>
            <td>${p.prescription_days || "7일"}</td>
        `;
        tbody.appendChild(tr);
    });
    
    // 글로벌 진단 ID 보존
    currentDiagnosisId = data.id;
    
    // PDF 발급 및 공유 이벤트 바인딩
    const triggerPdfGeneration = () => {
        const currentAddress = document.getElementById("address-input").value || "소재지 미지정";
        generatePDFReport(data.id, currentAddress);
    };
    
    const btnPdf = document.getElementById("btn-generate-pdf");
    if (btnPdf) {
        btnPdf.onclick = triggerPdfGeneration;
    }
    const btnPdfFinal = document.getElementById("btn-generate-pdf-final");
    if (btnPdfFinal) {
        btnPdfFinal.onclick = triggerPdfGeneration;
    }

    
    // 로컬 이력 대장에 저장
    saveToHistory(data);
}


// 10. 로컬 저장소 이력 저장 및 동기화
function saveToHistory(data) {
    let history = [];
    const saved = localStorage.getItem("aitreedoctor_mvp_history");
    if (saved) {
        try {
            history = JSON.parse(saved);
        } catch (e) {}
    }
    
    // 중복 방지
    if (!history.some(item => item.id === data.id)) {
        history.unshift({
            id: data.id,
            date: new Date().toISOString().slice(0, 10),
            user_id: appSettings.doctorName,
            address: data.address || "소재지 미지정",
            tree_species: data.tree_species,
            suspected_disease: data.suspected_disease,
            severity_level: data.severity_level,
            pdf_url: data.pdf_url || null,
            far_photo: selectedFarBase64, // 원경 수목 사진 저장
            close_photo: selectedCloseBase64, // 근경 수목 사진 저장
            extra_photos: extraPhotos || [], // 추가 등록 사진 저장
            status_leaves: data.status_leaves,
            status_stems: data.status_stems,
            status_roots: data.status_roots,
            treatment_method: data.treatment_method,
            status_leaves_summary: data.status_leaves_summary,
            status_stems_summary: data.status_stems_summary,
            status_roots_summary: data.status_roots_summary,
            treatment_method_summary: data.treatment_method_summary,
            pesticides: data.pesticides
        });
        localStorage.setItem("aitreedoctor_mvp_history", JSON.stringify(history));
    }
}

function loadHistoryTable() {
    let history = [];
    const saved = localStorage.getItem("aitreedoctor_mvp_history");
    if (saved) {
        try {
            history = JSON.parse(saved);
        } catch (e) {}
    }
    
    const container = document.getElementById("history-list-container");
    if (!container) return;
    
    if (history.length === 0) {
        container.innerHTML = `<div class="no-history-text">등록된 진단 내역이 없습니다. 첫 수목 진단을 진행해 주세요.</div>`;
        return;
    }
    
    container.innerHTML = "";
    history.forEach(item => {
        const card = document.createElement("div");
        card.className = "history-card";
        
        // PDF 단추 구성 (나무의사 회원 이상일 경우에만 노출)
        let pdfBtn = "";
        if (appSettings.userRole === "doctor") {
            const pdfUrlVal = item.pdf_url || item.pdfUrl;
            if (pdfUrlVal && pdfUrlVal !== "undefined") {
                pdfBtn = `
                    <a href="${BACKEND_URL}${pdfUrlVal}?t=${new Date().getTime()}" target="_blank" class="btn-card-action" style="text-decoration:none; display:inline-flex; align-items:center; justify-content:center;"><i class="fa-solid fa-file-pdf"></i> PDF 받기</a>
                    <button class="btn-card-action" onclick="generatePDFReport('${item.id}', '${item.address}')" style="margin-left: 4px;"><i class="fa-solid fa-arrows-rotate"></i> 재발행</button>
                `;
            } else {
                pdfBtn = `<button class="btn-card-action" onclick="generatePDFReport('${item.id}', '${item.address}')"><i class="fa-solid fa-file-pdf"></i> PDF 발행</button>`;
            }
        }
        
        card.innerHTML = `
            <div class="history-card-header">
                <span class="history-card-title">${item.tree_species} - ${item.suspected_disease}</span>
                <span class="badge-history-sev ${item.severity_level}">${item.severity_level}</span>
            </div>
            <div class="history-card-body">
                <p><i class="fa-solid fa-location-dot"></i> ${item.address}</p>
                <p><i class="fa-solid fa-user"></i> 의뢰인: ${item.user_id}</p>
            </div>
            <div class="history-card-footer">
                <span class="history-card-date">${item.date}</span>
                <div class="history-card-actions">
                    ${pdfBtn}
                    <button class="btn-card-action" onclick="viewSharedReport('${item.id}')"><i class="fa-solid fa-eye"></i> 상세</button>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}


function viewSharedReport(id) {
    window.open(`share.html?id=${id}`, "_blank");
}

// 11. PDF 리포트 발행 요청
function generatePDFReport(id, address) {
    // 로컬 이력에서 해당 ID를 찾아 사진 데이터 추출 (서버에 보내 PDF에 그리도록 함)
    const history = JSON.parse(localStorage.getItem("aitreedoctor_mvp_history") || "[]");
    const localItem = history.find(item => item.id === id);
    
    const reqBody = {
        diagnosis_id: id,
        doctor_name: appSettings.doctorName,
        license_number: appSettings.licenseNumber,
        hospital_name: appSettings.hospitalName,
        address: address,
        far_photo: localItem ? localItem.far_photo : selectedFarBase64,
        close_photo: localItem ? localItem.close_photo : selectedCloseBase64,
        extra_photos: localItem ? (localItem.extra_photos || []) : extraPhotos
    };
    
    fetch(`${BACKEND_URL}/api/v1/prescriptions/generate`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(reqBody)
    })
    .then(res => {
        if (!res.ok) throw new Error("서버 에러");
        return res.json();
    })
    .then(data => {
        const pdfUrlVal = data.pdf_url || data.pdfUrl;
        if (!pdfUrlVal) {
            console.error("서버 응답에 PDF URL이 없습니다.", data);
            alert("서버가 PDF 경로를 올바르게 반환하지 않았습니다.");
            return;
        }
        
        // PDF가 로컬 백엔드 서버에서 열리도록 팝업 (브라우저 캐시 방지를 위해 타임스탬프 추가)
        window.open(`${BACKEND_URL}${pdfUrlVal}?t=${new Date().getTime()}`, "_blank");
        
        // 로컬스토리지 pdf_url 상태 업데이트
        let history = JSON.parse(localStorage.getItem("aitreedoctor_mvp_history") || "[]");
        history = history.map(item => {
            if (item.id === id) {
                item.pdf_url = pdfUrlVal;
            }
            return item;
        });
        localStorage.setItem("aitreedoctor_mvp_history", JSON.stringify(history));
        loadHistoryTable();
    })
    .catch(err => {
        console.error("PDF 발행 중 에러 발생", err);
        alert("PDF 발행은 백엔드 서버(FastAPI)가 기동 중이어야 정상 동작합니다.\n백엔드 터미널 구동을 확인해 주세요.");
    });
}

// 12. 외부 농약정보 데이터 동기화
function syncPesticidesFromServer() {
    if (!confirm("외부 농약안전정보시스템(OpenAPI)으로부터 최신 등록 수목약제 고시 데이터를 가져와 동기화하시겠습니까?")) {
        return;
    }
    
    fetch(`${BACKEND_URL}/api/v1/sync/pesticides`, {
        method: "POST"
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(errData => {
                throw new Error(errData.detail || errData.message || "서버 에러가 발생했습니다.");
            }).catch(() => {
                throw new Error(`HTTP 에러: ${res.status}`);
            });
        }
        return res.json();
    })
    .then(data => {
        const title = (data.status === "success") ? "동기화 완료!" : "동기화 완료 (로컬 대체)!";
        alert(`${title}\n상태: ${data.status}\n메시지: ${data.message}\n신규 적재 항목: ${data.synchronized_count}건`);
    })
    .catch(err => {
        console.error("동기화 중 오류 발생", err);
        alert(`동기화 실패!\n사유: ${err.message}`);
    });
}

// 13. 새로운 모바일 처방전 공유 채널 기능
function shareViaKakao() {
    if (!currentDiagnosisId) {
        alert("공유할 진단 내역이 없습니다.");
        return;
    }
    const shareLink = `${window.location.origin}/share.html?id=${currentDiagnosisId}`;
    navigator.clipboard.writeText(shareLink).then(() => {
        alert("카카오톡 공유 링크가 클립보드에 복사되었습니다!\n카카오톡 대화방을 열어 붙여넣기(Ctrl+V) 하세요.\n\n링크: " + shareLink);
    }).catch(err => {
        console.error("복사 실패", err);
        alert("공유 링크: " + shareLink);
    });
}

function shareViaSMS() {
    if (!currentDiagnosisId) {
        alert("공유할 진단 내역이 없습니다.");
        return;
    }
    const shareLink = `${window.location.origin}/share.html?id=${currentDiagnosisId}`;
    const smsBody = `[AITreeDoctor] 수목 정밀 처방전이 발행되었습니다. 아래 링크에서 상세 내용을 확인하세요:\n${shareLink}`;
    // 모바일 네이티브 문자 발송 앱 연동
    window.location.href = `sms:?body=${encodeURIComponent(smsBody)}`;
}

function copyShareLink() {
    if (!currentDiagnosisId) {
        alert("공유할 진단 내역이 없습니다.");
        return;
    }
    const shareLink = `${window.location.origin}/share.html?id=${currentDiagnosisId}`;
    navigator.clipboard.writeText(shareLink).then(() => {
        alert("처방전 공유 링크가 클립보드에 복사되었습니다!");
    }).catch(err => {
        console.error("복사 실패", err);
        alert("공유 링크: " + shareLink);
    });
}

// 추가 현장 사진 파일 입력 트리거
function triggerExtraFileInput() {
    const fileInput = document.getElementById("extra-file-input");
    if (fileInput) fileInput.click();
}

// 추가 사진 업로드 처리 및 이미지 리사이징(압축)
function handleExtraFiles(input) {
    if (!input.files || input.files.length === 0) return;
    
    const remainingSlots = 3 - extraPhotos.length;
    if (remainingSlots <= 0) {
        alert("추가 사진은 최대 3장까지만 등록 가능합니다.");
        input.value = "";
        return;
    }
    
    const filesToProcess = Array.from(input.files).slice(0, remainingSlots);
    let processedCount = 0;
    
    filesToProcess.forEach(file => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                // 브라우저 Canvas를 활용한 이미지 압축 (최대 600px)
                const canvas = document.createElement("canvas");
                let width = img.width;
                let height = img.height;
                const maxDim = 600;
                
                if (width > maxDim || height > maxDim) {
                    if (width > height) {
                        height = Math.round((height * maxDim) / width);
                        width = maxDim;
                    } else {
                        width = Math.round((width * maxDim) / height);
                        height = maxDim;
                    }
                }
                
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0, width, height);
                
                // JPEG 포맷으로 압축률 0.7 적용
                const base64 = canvas.toDataURL("image/jpeg", 0.7);
                
                if (extraPhotos.length < 3) {
                    extraPhotos.push(base64);
                }
                
                processedCount++;
                if (processedCount === filesToProcess.length) {
                    input.value = ""; // 입력창 초기화
                    renderExtraPhotosGrid();
                    updateHistoryExtraPhotos();
                }
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    });
}

// 추가 사진 그리드 렌더링
function renderExtraPhotosGrid() {
    const grid = document.getElementById("additional-photos-grid");
    if (!grid) return;
    
    // btnWrapper를 안전하게 분리 보관
    let btnWrapper = document.getElementById("add-photo-btn-wrapper");
    if (btnWrapper) {
        btnWrapper.remove(); // 그리드에서 잠시 분리하여 초기화 방지
    } else {
        // 혹시라도 유실된 경우 재생성
        btnWrapper = document.createElement("div");
        btnWrapper.className = "add-photo-btn-wrapper";
        btnWrapper.id = "add-photo-btn-wrapper";
        btnWrapper.innerHTML = `
            <button type="button" class="btn-add-extra-photo" onclick="triggerExtraFileInput()">
                <i class="fa-solid fa-plus"></i>
            </button>
            <input type="file" id="extra-file-input" accept="image/*" multiple style="display: none;" onchange="handleExtraFiles(this)">
        `;
    }
    
    grid.innerHTML = "";
    
    extraPhotos.forEach((src, idx) => {
        const wrapper = document.createElement("div");
        wrapper.className = "extra-thumbnail-wrapper";
        wrapper.innerHTML = `
            <img src="${src}" alt="Extra Photo" class="extra-thumbnail">
            <button type="button" class="btn-remove-extra" onclick="removeExtraPhoto(${idx})"><i class="fa-solid fa-xmark"></i></button>
        `;
        grid.appendChild(wrapper);
    });
    
    // 3장 미만일 때만 추가 버튼 노출
    if (extraPhotos.length < 3) {
        grid.appendChild(btnWrapper);
    }
    
    // 추가 사진이 1장 이상이면 재진단 버튼 표시
    const btnReDiagnose = document.getElementById("btn-re-diagnose");
    if (btnReDiagnose) {
        btnReDiagnose.style.display = extraPhotos.length > 0 ? "block" : "none";
    }
}

// 추가 사진 삭제
function removeExtraPhoto(index) {
    extraPhotos.splice(index, 1);
    
    // 동일한 파일을 다시 선택할 수 있도록 input value 초기화
    const fileInput = document.getElementById("extra-file-input");
    if (fileInput) fileInput.value = "";
    
    renderExtraPhotosGrid();
    updateHistoryExtraPhotos();
}

// 추가 사진 초기화
function clearExtraPhotos() {
    extraPhotos = [];
    const fileInput = document.getElementById("extra-file-input");
    if (fileInput) fileInput.value = "";
    renderExtraPhotosGrid();
}

// 로컬 스토리지 이력 데이터의 추가 사진 업데이트
function updateHistoryExtraPhotos() {
    if (!currentDiagnosisId) return;
    let history = [];
    const saved = localStorage.getItem("aitreedoctor_mvp_history");
    if (saved) {
        try {
            history = JSON.parse(saved);
        } catch (e) {}
    }
    
    history = history.map(item => {
        if (item.id === currentDiagnosisId) {
            item.extra_photos = extraPhotos;
        }
        return item;
    });
    localStorage.setItem("aitreedoctor_mvp_history", JSON.stringify(history));
}

// 재진단 버튼 이벤트 리스너 추가
document.addEventListener("DOMContentLoaded", () => {
    const btnReDiagnose = document.getElementById("btn-re-diagnose");
    if (btnReDiagnose) {
        btnReDiagnose.addEventListener("click", () => {
            if (extraPhotos.length === 0) {
                alert("추가 현장 사진을 먼저 등록해 주세요.");
                return;
            }
            // 기존 결과창 숨기고 다시 스캔 실행
            const resultsContainer = document.getElementById("results-container");
            if (resultsContainer) resultsContainer.classList.add("hidden");
            
            triggerAutoScan();
        });
    }
});

// ─────────────────────────────────────────────
// AI 모델 학습 연구소와 공공 데이터 동기화 기능은 관리자 화면(admin.html/admin.js)으로 이관되었습니다.
// ─────────────────────────────────────────────
