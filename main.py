import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "log": "0", 
    "assets": "1068342666", 
    "inventory": "2138778159", 
    "pharmacy": "347265850"
}
# 새로 배포하신 앱스 스크립트 URL을 반드시 확인해 주세요!
API_URL = "https://script.google.com/macros/s/AKfycbzctUtHI2tRtNRoRRfr06xfTp0W9XkxSI1gHj8JPz_E6ftbidN8o8Lz32VbxjAfGLzj/exec"
COLOR_PRIMARY = "#4dabf7"

RECOMMENDED = {
    "칼로리": 2200, "단백질": 180, "탄수화물": 280, "지방": 85,
    "식이섬유": 30, "나트륨": 2300, "당류": 50, "콜레스테롤": 300, "수분(ml)": 2000     
}

# --- [2. 핵심 유틸리티] ---
def format_krw(val): return f"{int(val):,}".rjust(15) + " 원"

def to_numeric(val):
    if pd.isna(val) or val == "": return 0
    s = re.sub(r'[^0-9.-]', '', str(val))
    try: return float(s) if '.' in s else int(s)
    except: return 0

def extract_quantity(text):
    if pd.isna(text): return None
    match = re.search(r"([0-9]*\.[0-9]+|[0-9]+)", str(text))
    return float(match.group(1)) if match else None

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    ts = datetime.now().timestamp()
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={ts}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(payload):
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

def sync_full_sheet(gid_key, df):
    payload = {"action": "overwrite", "gid": GID_MAP[gid_key], "data": [df.columns.tolist()] + df.values.tolist()}
    return send_to_sheet(payload)

def get_period():
    today = datetime.now()
    if today.day >= 25:
        start = today.replace(day=25); end = (start + timedelta(days=32)).replace(day=24)
    else:
        end = today.replace(day=24); start = (end - timedelta(days=32)).replace(day=25)
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

# --- [3. UI 설정] ---
st.set_page_config(page_title="JARVIS v68.0 Family", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)
s_date, e_date = get_period()

st.markdown(f"""<style>thead tr th:first-child, tbody th {{ display:none; }} .status-card {{ background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_PRIMARY}; margin-bottom: 20px; }}</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ JARVIS Family")
    user_name = st.radio("사용자 선택", ["정원", "서진"])
    menu = st.radio("메뉴 선택", ["자산/정산 관리", "스마트 식단(재고연동)", "재고 관리"])
    st.divider()
    st.info(f"📅 현재 정산 주기\n{s_date} ~ {e_date}")

# --- [4. 메뉴별 기능 구현] ---

if menu == "자산/정산 관리":
    st.subheader(f"💰 {user_name}님 중심 통합 자산 관리")
    
    with st.sidebar:
        st.markdown("**💰 지출/수입 기록**")
        t_choice = st.selectbox("1. 구분 선택", ["지출", "수입"])
        cat_list = ["식비", "생활용품", "사회적 관계", "고정지출", "주거/통신", "교통", "건강", "금융", "자산이동", "기타지출"] if t_choice == "지출" else ["월급", "부수입", "용돈", "금융수입", "자산이동", "기타수입"]
        with st.form("asset_input_form"):
            c_main = st.selectbox("2. 분류 선택", cat_list)
            sel_date = st.date_input("날짜", value=now.date())
            content = st.text_input("상세 내용")
            a_input = st.number_input("금액", min_value=0, step=1000)
            method = st.selectbox("결제/입금처", ["계좌이체", "현금", "국민카드(WE:SH)", "하나카드(MG+)", "우리카드(주거래)", "현대카드(이마트)"])
            if st.form_submit_button("시트로 전송"):
                payload = {"time": f"{sel_date}", "corpus": "log", "type": t_choice, "cat_main": c_main, "item": content, "value": a_input, "method": method, "user": user_name}
                if a_input > 0 and send_to_sheet(payload):
                    st.success("기록 성공!"); st.cache_data.clear(); st.rerun()

    if st.button("🔄 매월 25일 장부 리셋 및 이월 실행"):
        if send_to_sheet({"action": "reset_ledger", "user": user_name}):
            st.success("정산 주기가 리셋되었습니다."); st.cache_data.clear(); st.rerun()

    df_assets = load_sheet_data(GID_MAP["assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, :3]; df_assets.columns = ["항목", "금액", "비고"]
        total_val, realtime_list = 0, []
        for i in range(len(df_assets)):
            item, val = str(df_assets.iloc[i, 0]), to_numeric(df_assets.iloc[i, 1])
            if not item or item == "nan" or item == "항목": continue
            realtime_list.append({"항목": item, "금액": val}); total_val += val
        
        st.markdown(f'<div class="status-card"><small>실시간 통합 순자산</small><br><span style="font-size:2.5em; font-weight:bold;">{total_val:,.0f} 원</span></div>', unsafe_allow_html=True)
        df_final = pd.DataFrame(realtime_list)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🟢 보유 자산")
            st.table(df_final[df_final["금액"] > 0].assign(금액=lambda x: x["금액"].apply(format_krw)))
        with col2:
            st.markdown("#### 🔴 부채 및 카드값")
            st.table(df_final[df_final["금액"] < 0].assign(금액=lambda x: x["금액"].apply(lambda v: format_krw(abs(v)))))

elif menu == "스마트 식단(재고연동)":
    st.subheader("🍴 스마트 식단 입력 (사용 시 재고 자동 차감)")
    df_inv = load_sheet_data(GID_MAP["inventory"])
    
    if not df_inv.empty:
        # [수정] 컬럼 이름에 의존하지 않고 인덱스(순서)로 접근하여 에러 방지
        items_list = df_inv.iloc[:, 0].tolist() # A열: 품목 리스트
        
        col1, col2 = st.columns([1, 1])
        with col1:
            with st.form("smart_diet_form"):
                food_item = st.selectbox("냉장고 품목 선택", items_list)
                use_weight = st.number_input("사용량 (g 단위)", min_value=0, step=10)
                submit_diet = st.form_submit_button("식사 기록 및 재고 차감")
                
                if submit_diet and use_weight > 0:
                    # 선택한 품목의 행 찾기
                    row = df_inv[df_inv.iloc[:, 0] == food_item].iloc[0]
                    
                    # 수식 에러 방지를 위해 열 번호로 접근 (0:품목, 1:수량, 3:칼로리, 4:단백질 가정)
                    # 정원님 시트 구조에 따라 숫자를 조정할 수 있습니다.
                    cal_val = to_numeric(row[3]) if len(row) > 3 else 0
                    prot_val = to_numeric(row[4]) if len(row) > 4 else 0
                    
                    cal_per_g = cal_val / 100
                    prot_per_g = prot_val / 100
                    
                    payload = {
                        "action": "diet_with_inventory", "user": user_name, "item": food_item, 
                        "weight": use_weight, "cal": cal_per_g * use_weight, 
                        "prot": prot_per_g * use_weight, "gid": GID_MAP["inventory"]
                    }
                    if send_to_sheet(payload):
                        st.success(f"✅ {food_item} {use_weight}g 차감 완료!"); st.cache_data.clear(); st.rerun()
        with col2:
            st.markdown("#### 오늘의 영양 요약")
            if 'daily_nutri' not in st.session_state: st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
            for k in ["칼로리", "단백질"]:
                v = st.session_state.daily_nutri.get(k, 0.0)
                st.write(f"**{k}**: {v:.1f} / {RECOMMENDED[k]}")
                st.progress(min(1.0, v / RECOMMENDED[k]))

elif menu == "재고 관리":
    st.subheader("📦 실시간 재고 및 단위 관리 (g/ml)")
    t1, t2 = st.tabs(["🍎 식재료 재고", "💊 상비약 현황"])
    with t1:
        df_inv = load_sheet_data(GID_MAP["inventory"])
        if not df_inv.empty:
            edited_inv = st.data_editor(df_inv, num_rows="dynamic", use_container_width=True, key="ed_inv_v68")
            if st.button("식재료 데이터 최종 저장"):
                if sync_full_sheet("inventory", edited_inv):
                    st.success("재고 동기화 완료!"); st.cache_data.clear(); st.rerun()
    with t2:
        df_pharma = load_sheet_data(GID_MAP["pharmacy"])
        if not df_pharma.empty:
            edited_ph = st.data_editor(df_pharma, num_rows="dynamic", use_container_width=True, key="ed_ph_v68")
            if st.button("상비약 데이터 최종 저장"):
                if sync_full_sheet("pharmacy", edited_ph):
                    st.success("상비약 업데이트 완료!"); st.cache_data.clear(); st.rerun()
