// AITreeDoctor Admin Panel JavaScript Logic

const BACKEND_URL = window.location.origin;

let trainingPollInterval = null;
let trainLossHistory = [];
let trainAccHistory = [];

document.addEventListener("DOMContentLoaded", () => {
    // 초기 시작 시 대시보드 탭 로드
    switchAdminTab("tab-admin-dashboard");
    initDatasetLoader();
});

// ─────────────────────────────────────────────
// 사이드바 탭 전환 및 탭별 액션
// ─────────────────────────────────────────────
function switchAdminTab(tabId) {
    // 1. 모든 탭 숨기기
    document.querySelectorAll(".admin-tab-content").forEach(tab => {
        tab.classList.add("hidden");
        tab.classList.remove("active");
    });
    
    // 2. 대상 탭 활성화
    const targetTab = document.getElementById(tabId);
    if (targetTab) {
        targetTab.classList.remove("hidden");
        targetTab.classList.add("active");
    }
    
    // 3. 사이드바 아이템 활성화 상태 업데이트
    document.querySelectorAll(".sidebar-item").forEach(item => {
        item.classList.remove("active");
    });
    
    // 클릭된 사이드바 아이템에 active 부여
    const clickedItem = Array.from(document.querySelectorAll(".sidebar-item")).find(item => 
        item.getAttribute("onclick").includes(tabId)
    );
    if (clickedItem) clickedItem.classList.add("active");
    
    // 4. 탭별 로딩 액션
    if (tabId === "tab-admin-dashboard") {
        loadDashboardStats();
    } else if (tabId === "tab-admin-models") {
        loadModelsFromServer();
    } else if (tabId === "tab-admin-ncpms") {
        loadNCPMSForecasts();
        loadNCPMSLocalList();
    }
}

// ─────────────────────────────────────────────
// 시스템 대시보드 홈 메트릭 로딩
// ─────────────────────────────────────────────
function loadDashboardStats() {
    fetch(`${BACKEND_URL}/api/v1/training/stats`)
    .then(res => {
        if (!res.ok) throw new Error("스펙 조회 실패");
        return res.json();
    })
    .then(data => {
        document.getElementById("stat-total-diagnoses").innerText = `${data.total_diagnoses}건`;
        document.getElementById("stat-active-engine").innerText = data.active_engine;
        document.getElementById("stat-total-pesticides").innerText = `${data.total_pesticides}개`;
    })
    .catch(err => {
        console.error("대시보드 통계 로드 오류", err);
        document.getElementById("stat-total-diagnoses").innerText = "오류";
        document.getElementById("stat-active-engine").innerText = "오류";
        document.getElementById("stat-total-pesticides").innerText = "오류";
    });
}

// ─────────────────────────────────────────────
// AI-Hub 데이터셋 로더 (드래그 앤 드롭)
// ─────────────────────────────────────────────
function initDatasetLoader() {
    const dropZone = document.getElementById("dataset-drop-zone");
    const fileInput = document.getElementById("dataset-file-input");
    const statusMsg = document.getElementById("dataset-status-msg");
    
    if (!dropZone || !fileInput) return;
    
    dropZone.addEventListener("click", () => fileInput.click());
    
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleDatasetFile(fileInput.files[0]);
        }
    });
    
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "var(--accent)";
        dropZone.style.backgroundColor = "rgba(16, 185, 129, 0.05)";
    });
    
    dropZone.addEventListener("dragleave", () => {
        dropZone.style.borderColor = "var(--border)";
        dropZone.style.backgroundColor = "rgba(255, 255, 255, 0.02)";
    });
    
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "var(--border)";
        dropZone.style.backgroundColor = "rgba(255, 255, 255, 0.02)";
        if (e.dataTransfer.files.length > 0) {
            handleDatasetFile(e.dataTransfer.files[0]);
        }
    });
    
    function handleDatasetFile(file) {
        if (!file.name.endsWith(".zip")) {
            statusMsg.style.color = "#ef4444";
            statusMsg.innerText = "오류: AI-Hub 데이터셋 파일은 .zip 형식만 가능합니다.";
            return;
        }
        statusMsg.style.color = "var(--accent)";
        statusMsg.innerText = `적재 성공: ${file.name} (${(file.size / 1024 / 1024).toFixed(1)}MB) - 학습 대기 중`;
    }
}

// ─────────────────────────────────────────────
// AI 모델 관리 및 활성화 설정
// ─────────────────────────────────────────────
function loadModelsFromServer() {
    fetch(`${BACKEND_URL}/api/v1/training/models`)
    .then(res => {
        if (!res.ok) throw new Error("모델 조회 실패");
        return res.json();
    })
    .then(models => {
        const select = document.getElementById("active-model-select");
        if (!select) return;
        
        select.innerHTML = "";
        models.forEach(model => {
            const opt = document.createElement("option");
            opt.value = model.model_id;
            opt.innerText = `${model.model_name} (Acc: ${(model.accuracy * 100).toFixed(1)}%, Loss: ${model.loss.toFixed(3)}) ${model.status === 'active' ? '[사용 중]' : ''}`;
            if (model.status === "active") {
                opt.selected = true;
            }
            select.appendChild(opt);
        });
    })
    .catch(err => {
        console.error("AI 모델 로드 오류", err);
    });
}

function switchActiveModel() {
    const select = document.getElementById("active-model-select");
    if (!select) return;
    const modelId = select.value;
    
    fetch(`${BACKEND_URL}/api/v1/training/activate`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ model_id: modelId })
    })
    .then(res => {
        if (!res.ok) throw new Error("전환 실패");
        return res.json();
    })
    .then(data => {
        alert(data.message);
        loadModelsFromServer();
    })
    .catch(err => {
        console.error("모델 활성화 중 에러", err);
        alert("모델 활성화 변경 중 에러가 발생했습니다.");
    });
}

// ─────────────────────────────────────────────
// AI 모델 파인튜닝 시뮬레이터 실행
// ─────────────────────────────────────────────
function startFineTuning() {
    const datasetPath = document.getElementById("dataset-path-input").value || "";
    const epochs = parseInt(document.getElementById("train-epochs").value) || 5;
    const lr = parseFloat(document.getElementById("train-lr").value) || 0.001;
    const batchSize = parseInt(document.getElementById("train-batch-size").value) || 32;
    
    if (!datasetPath) {
        alert("데이터셋 로컬 경로를 지정해 주세요.");
        return;
    }
    
    const reqBody = {
        dataset_path: datasetPath,
        epochs: epochs,
        lr: lr,
        batch_size: batchSize
    };
    
    const dashboard = document.getElementById("training-dashboard");
    dashboard.classList.remove("hidden");
    
    const btn = document.getElementById("btn-start-training");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 파인튜닝 학습 진행 중...`;
    
    trainLossHistory = [];
    trainAccHistory = [];
    
    fetch(`${BACKEND_URL}/api/v1/training/start`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(reqBody)
    })
    .then(res => {
        if (!res.ok) return res.json().then(e => { throw new Error(e.detail); });
        return res.json();
    })
    .then(data => {
        if (trainingPollInterval) clearInterval(trainingPollInterval);
        trainingPollInterval = setInterval(pollTrainingStatus, 1500);
    })
    .catch(err => {
        console.error("학습 시작 오류", err);
        alert("학습을 시작할 수 없습니다: " + err.message);
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-play"></i> 파인튜닝 학습 시작`;
    });
}

function pollTrainingStatus() {
    fetch(`${BACKEND_URL}/api/v1/training/status`)
    .then(res => res.json())
    .then(data => {
        document.getElementById("metrics-epoch").innerText = `${data.current_epoch} / ${data.total_epochs}`;
        document.getElementById("metrics-loss").innerText = data.loss.toFixed(4);
        document.getElementById("metrics-acc").innerText = `${(data.accuracy * 100).toFixed(2)}%`;
        
        document.getElementById("training-progress-fill").style.width = `${data.progress}%`;
        document.getElementById("training-progress-text").innerText = `전체 진행률: ${data.progress}%`;
        
        const consoleEl = document.getElementById("terminal-console");
        consoleEl.innerHTML = "";
        data.logs.forEach(log => {
            const div = document.createElement("div");
            div.className = "log-line";
            if (log.startsWith("[SYSTEM]")) div.classList.add("system");
            else if (log.startsWith("[DATASET]")) div.classList.add("dataset");
            else if (log.includes("[ERROR]")) div.classList.add("error");
            div.innerText = log;
            consoleEl.appendChild(div);
        });
        consoleEl.scrollTop = consoleEl.scrollHeight;
        
        if (data.is_training) {
            const lastLoss = trainLossHistory[trainLossHistory.length - 1];
            const lastAcc = trainAccHistory[trainAccHistory.length - 1];
            if (trainLossHistory.length === 0 || lastLoss !== data.loss || lastAcc !== data.accuracy) {
                trainLossHistory.push(data.loss);
                trainAccHistory.push(data.accuracy);
                drawTrainingCharts();
            }
        }
        
        if (!data.is_training && data.progress >= 100) {
            clearInterval(trainingPollInterval);
            trainingPollInterval = null;
            
            trainLossHistory.push(data.loss);
            trainAccHistory.push(data.accuracy);
            drawTrainingCharts();
            
            alert("축하합니다! AI 모델 파인튜닝 학습이 완료되었습니다.\n새 커스텀 모델 ResNet50 v1.1이 등록되었습니다.");
            
            const btn = document.getElementById("btn-start-training");
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-play"></i> 파인튜닝 학습 시작`;
            
            loadModelsFromServer();
        }
    })
    .catch(err => {
        console.error("상태 폴링 오류", err);
    });
}

function drawTrainingCharts() {
    const canvas = document.getElementById("training-chart");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = width;
    canvas.height = height;
    
    ctx.clearRect(0, 0, width, height);
    
    const padL = 35;
    const padR = 35;
    const padT = 20;
    const padB = 20;
    
    const chartW = width - padL - padR;
    const chartH = height - padT - padB;
    
    ctx.strokeStyle = "rgba(255,255,255,0.05)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padT + (chartH * i / 4);
        ctx.beginPath();
        ctx.moveTo(padL, y);
        ctx.lineTo(width - padR, y);
        ctx.stroke();
    }
    
    const n = trainLossHistory.length;
    if (n < 2) {
        ctx.fillStyle = "rgba(255,255,255,0.4)";
        ctx.font = "10px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("학습 진행 데이터 수집 중...", width / 2, height / 2);
        return;
    }
    
    // [1] Loss
    ctx.strokeStyle = "#f97316";
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
        const x = padL + (chartW * i / (n - 1));
        const val = trainLossHistory[i];
        const y = padT + chartH * (1 - (val / 1.5));
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.stroke();
    
    // [2] Accuracy
    ctx.strokeStyle = "#10b981";
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
        const x = padL + (chartW * i / (n - 1));
        const val = trainAccHistory[i];
        const ratio = (val - 0.4) / 0.6;
        const y = padT + chartH * (1 - ratio);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.stroke();
    
    ctx.fillStyle = "#f97316";
    ctx.font = "8px monospace";
    ctx.textAlign = "right";
    ctx.fillText("L:1.5", padL - 5, padT + 3);
    ctx.fillText("L:0.0", padL - 5, height - padB);
    
    ctx.fillStyle = "#10b981";
    ctx.textAlign = "left";
    ctx.fillText("A:100%", width - padR + 5, padT + 3);
    ctx.fillText("A:40%", width - padR + 5, height - padB);
}

// ─────────────────────────────────────────────
// 공공 데이터 동기화 액션
// ─────────────────────────────────────────────
function syncPesticidesFromServer() {
    if (!confirm("외부 농약안전정보시스템(OpenAPI)으로부터 최신 등록 수목약제 고시 데이터를 가져와 동기화하시겠습니까?")) {
        return;
    }
    
    const btn = document.getElementById("btn-sync-pesticides");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 동기화 진행 중...`;
    
    fetch(`${BACKEND_URL}/api/v1/sync/pesticides`, {
        method: "POST"
    })
    .then(res => res.json())
    .then(data => {
        alert(`동기화 성공!\n상태: ${data.status}\n메시지: ${data.message}\n신규 적재 항목: ${data.synchronized_count}건`);
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> 동기화 실행`;
        loadDashboardStats(); // 메트릭 업데이트
    })
    .catch(err => {
        console.error("동기화 중 오류 발생", err);
        alert("농약 데이터 동기화 중 오류가 발생했습니다.");
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> 동기화 실행`;
    });
}

// ─────────────────────────────────────────────
// NCPMS OpenAPI 연동 센터 기능
// ─────────────────────────────────────────────
let selectedNCPMSDetail = null;

// 1. 전국 병해충 예찰 경보 로드
function loadNCPMSForecasts() {
    const container = document.getElementById("ncpms-forecast-container");
    if (!container) return;
    
    fetch(`${BACKEND_URL}/api/v1/ncpms/forecast`)
    .then(res => res.json())
    .then(data => {
        container.innerHTML = "";
        data.forEach(item => {
            const card = document.createElement("div");
            // 경보 레벨에 따른 스타일 설정
            let levelColor = "#3b82f6"; // 파랑
            let levelBg = "rgba(59, 130, 246, 0.08)";
            if (item.level === "경보") {
                levelColor = "#ef4444"; // 빨강
                levelBg = "rgba(239, 68, 68, 0.08)";
            } else if (item.level === "주의보") {
                levelColor = "#f59e0b"; // 주황
                levelBg = "rgba(245, 158, 11, 0.08)";
            }
            
            card.style.cssText = `
                padding: 12px;
                background-color: ${levelBg};
                border: 1px solid rgba(255,255,255,0.03);
                border-left: 4px solid ${levelColor};
                border-radius: 6px;
                display: flex;
                flex-direction: column;
                gap: 5px;
            `;
            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="font-size: 12px; color: #ffffff;">${item.title}</strong>
                    <span style="font-size: 8px; font-weight: 800; background-color: ${levelColor}; color: #ffffff; padding: 2px 6px; border-radius: 10px;">${item.level}</span>
                </div>
                <p style="margin: 0; font-size: 10.5px; color: var(--text-muted); line-height: 1.4;">${item.content}</p>
                <span style="font-size: 9px; color: var(--text-muted); text-align: right; font-family: monospace;">발생일: ${item.publishDate}</span>
            `;
            container.appendChild(card);
        });
    })
    .catch(err => {
        console.error("예찰 경보 조회 실패", err);
        container.innerHTML = `<div style="font-size: 11px; color: #ef4444;">예찰 정보를 불러올 수 없습니다.</div>`;
    });
}

// 2. 실시간 병해충 검색
function searchNCPMSPests() {
    const cropName = document.getElementById("ncpms-search-crop").value.trim();
    const sickName = document.getElementById("ncpms-search-sick").value.trim();
    
    if (!cropName) {
        alert("수종(작물)명을 먼저 입력하십시오.");
        return;
    }
    
    const btn = document.getElementById("btn-ncpms-search");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> NCPMS 연동 조회 중...`;
    
    let url = `${BACKEND_URL}/api/v1/ncpms/search?cropName=${encodeURIComponent(cropName)}`;
    if (sickName) {
        url += `&sickNameKor=${encodeURIComponent(sickName)}`;
    }
    
    const resultsGrid = document.getElementById("ncpms-search-results");
    resultsGrid.innerHTML = `<div style="font-size: 11px; color: var(--text-muted); grid-column: 1/-1; text-align: center; padding: 20px 0;"><i class="fa-solid fa-spinner fa-spin"></i> 로딩 중...</div>`;
    
    // 상세 정보 콘솔 창 숨기기
    document.getElementById("ncpms-detail-console").classList.add("hidden");
    
    fetch(url)
    .then(res => res.json())
    .then(data => {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-search"></i> NCPMS 실시간 검색`;
        
        if (data.length === 0) {
            resultsGrid.innerHTML = `<div style="font-size: 11px; color: var(--text-muted); grid-column: 1/-1; text-align: center; padding: 20px 0;">조회된 병해 데이터가 없습니다.</div>`;
            return;
        }
        
        resultsGrid.innerHTML = "";
        data.forEach(item => {
            const card = document.createElement("div");
            card.style.cssText = `
                background-color: rgba(255,255,255,0.02);
                border: 1px solid var(--border);
                border-radius: 6px;
                padding: 10px;
                cursor: pointer;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                gap: 10px;
            `;
            
            // Hover 효과 바인딩
            card.onmouseover = () => {
                card.style.borderColor = "var(--accent)";
                card.style.backgroundColor = "rgba(16, 185, 129, 0.04)";
            };
            card.onmouseout = () => {
                card.style.borderColor = "var(--border)";
                card.style.backgroundColor = "rgba(255,255,255,0.02)";
            };
            
            card.onclick = () => selectNCPMSItem(item.sickKey);
            
            const imgHtml = item.thumbImg ? `<img src="${item.thumbImg}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;">` : `<div style="width: 40px; height: 40px; border-radius: 4px; background: rgba(255,255,255,0.03); display: flex; align-items: center; justify-content: center; border: 1px solid var(--border);"><i class="fa-solid fa-image" style="font-size:16px; color:var(--border);"></i></div>`;
            
            card.innerHTML = `
                ${imgHtml}
                <div style="flex:1; display:flex; flex-direction:column; gap:2px; overflow:hidden;">
                    <span style="font-size:11.5px; font-weight:800; color:#ffffff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${item.sickNameKor}</span>
                    <span style="font-size:9.5px; color:var(--text-muted);">${item.cropName}</span>
                </div>
            `;
            resultsGrid.appendChild(card);
        });
    })
    .catch(err => {
        console.error("NCPMS 검색 실패", err);
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-search"></i> NCPMS 실시간 검색`;
        resultsGrid.innerHTML = `<div style="font-size: 11px; color: #ef4444; grid-column: 1/-1; text-align: center; padding: 20px 0;">오류: NCPMS 연동 검색 실패</div>`;
    });
}

// 3. 검색 결과 아이템 클릭 시 상세 조회
function selectNCPMSItem(sickKey) {
    const detailConsole = document.getElementById("ncpms-detail-console");
    detailConsole.classList.remove("hidden");
    
    // 로딩 표시
    document.getElementById("ncpms-detail-title").innerText = "상세 정보 조회 중...";
    document.getElementById("ncpms-detail-env").innerText = "로딩 중...";
    document.getElementById("ncpms-detail-symptoms").innerText = "로딩 중...";
    document.getElementById("ncpms-detail-prevention").innerText = "로딩 중...";
    document.getElementById("ncpms-detail-img").style.display = "none";
    document.getElementById("ncpms-detail-img-placeholder").style.display = "block";
    
    fetch(`${BACKEND_URL}/api/v1/ncpms/detail/${sickKey}`)
    .then(res => res.json())
    .then(data => {
        selectedNCPMSDetail = data; // 동기화에 사용할 글로벌 변수 저장
        
        document.getElementById("ncpms-detail-title").innerText = `${data.cropName} - ${data.sickNameKor}`;
        document.getElementById("ncpms-detail-env").innerText = data.developmentEnv || "상세 정보 없음.";
        document.getElementById("ncpms-detail-symptoms").innerText = data.symptoms || "상세 정보 없음.";
        document.getElementById("ncpms-detail-prevention").innerText = data.preventionMethod || "상세 정보 없음.";
        
        const imgEl = document.getElementById("ncpms-detail-img");
        const placeholderEl = document.getElementById("ncpms-detail-img-placeholder");
        
        if (data.imageUrl) {
            imgEl.src = data.imageUrl;
            imgEl.style.display = "block";
            placeholderEl.style.display = "none";
        } else {
            imgEl.style.display = "none";
            placeholderEl.style.display = "block";
        }
        
        // 콘솔로 스크롤 이동
        detailConsole.scrollIntoView({ behavior: 'smooth' });
    })
    .catch(err => {
        console.error("NCPMS 상세정보 로드 실패", err);
        alert("상세 정보를 가져올 수 없습니다.");
    });
}

// 4. 선택한 병해 정보를 로컬 DB에 동기화 적재
function syncSelectedToLocal() {
    if (!selectedNCPMSDetail) {
        alert("선택된 병해 정보가 없습니다.");
        return;
    }
    
    const btn = document.getElementById("btn-ncpms-sync");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 로컬 DB에 수집 적재 중...`;
    
    fetch(`${BACKEND_URL}/api/v1/ncpms/sync`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            sickKey: selectedNCPMSDetail.sickKey,
            sickNameKor: selectedNCPMSDetail.sickNameKor,
            cropName: selectedNCPMSDetail.cropName,
            developmentEnv: selectedNCPMSDetail.developmentEnv,
            symptoms: selectedNCPMSDetail.symptoms,
            preventionMethod: selectedNCPMSDetail.preventionMethod,
            imageUrl: selectedNCPMSDetail.imageUrl
        })
    })
    .then(res => {
        if (!res.ok) throw new Error("로컬 동기화 실패");
        return res.json();
    })
    .then(data => {
        alert(data.message);
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> 이 질병 정보를 로컬 DB에 동기화`;
        
        loadNCPMSLocalList(); // 적재된 테이블 갱신
        loadDashboardStats(); // 대시보드 통계 갱신
    })
    .catch(err => {
        console.error("로컬 적재 중 오류", err);
        alert("로컬 DB 동기화 적재 도중 오류가 발생했습니다.");
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> 이 질병 정보를 로컬 DB에 동기화`;
    });
}

// 5. 로컬에 동기화 수집된 라이브러리 목록 로드
function loadNCPMSLocalList() {
    const tbody = document.getElementById("ncpms-local-tbody");
    if (!tbody) return;
    
    fetch(`${BACKEND_URL}/api/v1/ncpms/local-list`)
    .then(res => res.json())
    .then(data => {
        if (data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="3" class="text-center" style="color: var(--text-muted); padding: 15px 0;">동기화된 지식 데이터가 없습니다.</td></tr>`;
            return;
        }
        
        tbody.innerHTML = "";
        data.forEach(item => {
            const tr = document.createElement("tr");
            
            // 날짜 포맷팅
            const dateStr = item.createdAt ? item.createdAt.substring(0, 16).replace("T", " ") : "-";
            
            tr.innerHTML = `
                <td><strong>${item.cropName}</strong></td>
                <td><span style="color:var(--accent); font-weight:700;">${item.sickNameKor}</span></td>
                <td style="font-family:monospace; color:var(--text-muted);">${dateStr}</td>
            `;
            tbody.appendChild(tr);
        });
    })
    .catch(err => {
        console.error("로컬 지식 리스트 로드 실패", err);
    });
}
