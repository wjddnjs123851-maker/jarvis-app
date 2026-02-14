import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532", "Health": "123456789"}
# OpenAI 또는 Google Vision API Key 입력 자리 (보스가 발급 후 기입)
VISION_API_KEY = "YOUR_API_KEY_HERE" 

DAILY_GUIDE = {
    "칼로리": {"val": 2900.0, "unit": "kcal"}, "지방": {"val": 90.0, "unit": "g"},
    "콜레스테롤": {"val": 300.0, "unit": "mg"}, "나트륨": {"val": 2300.0, "unit": "mg"},
    "탄수화물": {"val": 360.0, "unit": "g"}, "식이섬유": {"val": 30.0, "unit": "g"},
    "당": {"val": 50.0, "unit": "g"}, "단백질": {"val": 160.0, "unit": "g"}
}

FIXED_DATA = {
    "stocks": {
        "삼성전자": {"평단": 78895, "수량": 46}, "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성중공업": {"평단": 16761, "수량": 88}, "동성화인텍": {"평단": 22701, "수량": 21}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400}, "ETH": {"평단": 4243000, "수량": 0.03417393}
    }
}

# --- [2. 유틸리티] ---
def format_krw(val): return f"{int(val):,}" + "원"
def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def send_to_sheet(d_type, item, value, corpus="Log"):
    payload = {"time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "corpus": corpus, "type": d_type, "item": item, "value": value}
    try: return requests.post("https://script.google.com/macros/s/.../exec", data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: return pd.read_csv(url).dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정 및 UI] ---
st.set_page_config(page_title="JARVIS v36.0 - Shared Life", layout="wide")

# CSS: 가독성 및 2인 가구 모드 스타일
st.markdown("""<style>
    .stTable td { text-align: right !important; }
    .alert-box { background-color: #fff3f3; padding: 15px; border-left: 5px solid #ff4b4b; border-radius: 5px; margin-bottom: 20px; }
    .net-wealth { font-size: 2.2em; font-weight: bold; color: #1E90FF; border-top: 3px solid #1E90FF; padding-top: 10px; }
    .shared-badge { background-color: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# [능동형 비서] 상단 알림 위젯
st.markdown("### 🚨 실시간 시스템 알림")
a_c1, a_c2 = st.columns(2)
with a_c1:
    st.markdown('<div class="alert-box"><b>⚠️ 소비 임박 식자재:</b> 냉동 삼치(D-84), 냉동닭다리살(D-106)</div>', unsafe_allow_html=True)
with a_c2:
    st.markdown('<div class="alert-box" style="border-left-color: #ffa000; background-color: #fff8e1;"><b>⏰ 교체 알림:</b> 면도날 교체일이 1일 지났습니다.</div>', unsafe_allow_html=True)

# 사이드바
with st.sidebar:
    st.title("JARVIS v36.0")
    st.info("💍 약혼녀분과의 합가를 축하드립니다!")
    menu = st.radio("메뉴 선택", ["자산 & 공동지출", "인공지능 식단분석", "재고 & 생필품"])

# --- [4. 메인 화면 로직] ---

if menu == "자산 & 공동지출":
    st.header("💰 자산 및 공동 지출 관리")
    st.markdown('<div class="input-card" style="background:#f8f9fa; padding:15px; border-radius:10px; border:1px solid #ddd;">', unsafe_allow_html=True)
    f_c1, f_c2, f_c3, f_c4 = st.columns([1, 2, 2, 1])
    with f_c1: t_choice = st.selectbox("구분", ["지출", "수입", "공동생활비"])
    with f_c2: 
        cats = ["식비(공동)", "주거/공과금", "결혼준비", "가전/가구", "생활용품"] if t_choice == "공동생활비" else ["식비", "교통", "건강", "기타"]
        c_choice = st.selectbox("카테고리", cats)
    with f_c3: a_input = st.number_input("금액(원)", min_value=0, step=1000)
    with f_c4: 
        st.write(""); st.write("")
        if st.button("기록"): st.success("기록 완료")
    st.markdown('</div>', unsafe_allow_html=True)

    # 자산 데이터 (기존 데이터 무결성 유지)
    df_sheet = load_sheet_data(GID_MAP["Assets"])
    if not df_sheet.empty: 
        df_sheet.columns = ["항목", "금액"]
        df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
    
    # 주식/코인 데이터 포함
    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items(): inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})
    df_total = pd.concat([df_sheet, pd.DataFrame(inv_rows)], ignore_index=True)
    
    sum_a = df_total[df_total["val"] >= 0]["val"].sum()
    sum_l = abs(df_total[df_total["val"] < 0]["val"].sum())
    
    st.markdown(f'<div class="net-wealth">종합 순자산: {format_krw(sum_a - sum_l)}</div>', unsafe_allow_html=True)
    st.table(df_total.assign(금액=df_total["val"].apply(format_krw))[["항목", "금액"]])

elif menu == "인공지능 식단분석":
    st.header("📸 AI 식단 분석 (FatSecret 연동)")
    st.write("직접 입력하지 마세요. FatSecret 요약 화면을 캡처해서 올리시면 됩니다.")
    
    up_file = st.file_uploader("FatSecret 스크린샷 또는 음식 사진 업로드", type=["jpg", "png", "jpeg"])
    
    if up_file:
        st.image(up_file, caption="분석 중...", width=300)
        # TODO: Vision API 연동 로직 (보스가 API 키 입력 시 활성화)
        st.warning("Vision API 연동 시 자동으로 영양소가 기입됩니다. (현재는 수동 확인 모드)")
    
    st.divider()
    # 기존 영양소 수동 입력창 (백업용 유지)
    with st.expander("수동 영양소 입력 (필요시)"):
        in_kcal = st.number_input("칼로리", 0.0, format="%.2f")
        if st.button("데이터 전송"): st.rerun()

elif menu == "재고 & 생필품":
    st.header("📦 2인 가구 통합 재고 관리")
    # 식자재 데이터 보존 (Zero-Deletion)
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"항목": "냉동 삼치", "수량": "4팩", "유통기한": "2026-05-10"}, {"항목": "냉동닭다리살", "수량": "3팩단위", "유통기한": "2026-06-01"},
            {"항목": "단백질 쉐이크", "수량": "9개", "유통기한": "2026-12-30"}, {"항목": "카무트/쌀 혼합", "수량": "2kg", "유통기한": "2026-10-20"},
            {"항목": "파스타면", "수량": "대량", "유통기한": "-"}, {"항목": "소면", "수량": "1봉", "유통기한": "-"},
            {"항목": "쿠스쿠스", "수량": "500g", "유통기한": "2027-01-01"}, {"항목": "우동사리", "수량": "3봉", "유통기한": "-"},
            {"항목": "라면", "수량": "6봉", "유통기한": "-"}, {"항목": "토마토 페이스트", "수량": "10캔", "유통기한": "2027-05-15"},
            {"항목": "나시고랭 소스", "수량": "1팩", "유통기한": "2026-11-20"}, {"항목": "치아씨드/아사이베리", "수량": "보유", "유통기한": "-"},
            {"항목": "김치 4종", "수량": "보유", "유통기한": "-"}, {"항목": "당근", "수량": "보유", "유통기한": "-"}, {"항목": "감자", "수량": "보유", "유통기한": "-"}
        ])
    st.data_editor(st.session_state.inventory, use_container_width=True)
    
    st.divider()
    # 생활용품 교체 주기
    if 'supplies' not in st.session_state:
        st.session_state.supplies = pd.DataFrame([
            {"품목": "칫솔(보스)", "최근교체일": "2026-01-15", "주기": 30},
            {"품목": "칫솔(약혼녀)", "최근교체일": "2026-02-15", "주기": 30},
            {"품목": "면도날", "최근교체일": "2026-02-01", "주기": 14}
        ])
    st.data_editor(st.session_state.supplies, use_container_width=True)
