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
    "pharmacy": "347265850",
    "replacement": "928688150" # 요청하신 GID로 수정
}
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"

# --- [2. 핵심 방탄 유틸리티] ---
def to_numeric(val):
    """모든 형식의 데이터를 안전하게 숫자로 변환 (부채 마이너스 보존)"""
    if pd.isna(val) or str(val).strip() == "": return 0.0
    s = str(val).replace(',', '').replace(' ', '').strip()
    if s.startswith('(') and s.endswith(')'): s = '-' + s[1:-1]
    try:
        match = re.search(r"(-?\d*\.\d+|-?\d+)", s)
        return float(match.group(1)) if match else 0.0
    except: return 0.0

@st.cache_data(ttl=15)
def get_coin_price(ticker):
    try:
        res = requests.get(f"https://api.upbit.com/v1/ticker?markets=KRW-{ticker.upper()}", timeout=2).json()
        return float(res[0]['trade_price'])
    except: return None

@st.cache_data(ttl=300)
def get_weather(city="Pyeongtaek"):
    try:
        res = requests.get(f"https://wttr.in/{city}?format=j1").json()
        curr = res['current_condition'][0]
        return f"🌡️ {curr['temp_C']}°C | 💧 {curr['humidity']}% | {curr['weatherDesc'][0]['value']}"
    except: return "날씨 정보를 불러올 수 없습니다."

@st.cache_data(ttl=5)
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url).dropna(how='all')
        return df
    except: return pd.DataFrame()

def sync_sheet(payload):
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

# --- [3. UI 설정] ---
st.set_page_config(page_title="JARVIS Prime v81.0", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

# CSS: 인덱스 열 숨기기 및 스타일 적용
st.markdown("""
<style>
    thead tr th:first-child, tbody th { display:none; }
    .metric-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; text-align: center; margin-bottom: 15px; }
    .stTable { font-size: 0.9em; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ 자비스 마스터")
    st.info(f"📍 평택시 날씨: {get_weather('Pyeongtaek')}")
    menu = st.radio("메뉴", ["💰 자산/가계부", "🥩 식단/재고", "📅 생활 관리", "💊 상비약 관리"])
    st.divider()

# --- [4. 메뉴별 기능 구현] ---

if menu == "💰 자산/가계부":
    st.header("📊 통합 자산 리포트 및 가계부")
    
    with st.sidebar:
        st.subheader("💸 가계부 빠른 입력")
        t_type = st.selectbox("구분", ["지출", "수입"])
        # 카테고리 슬림화 (정원 님 이미지 기준)
        cats = ["식비", "관리비/공과금", "주거/임대", "통신비", "보험료", "의료/건강", "교통/차량", "생활용품", "여가/문화", "기타"]
        methods = ["현금", "계좌이체", "국민카드", "우리카드", "하나카드", "현대카드"]
        
        with st.form("log_form"):
            c_main = st.selectbox("카테고리", cats)
            item_name = st.text_input("내용")
            amount = st.number_input("금액", min_value=0, step=1000)
            pay_method = st.selectbox("결제수단", methods)
            
            if st.form_submit_button("시트로 기록 및 자산 반영"):
                df_assets = load_data(GID_MAP["assets"])
                target = "가용현금" if pay_method in ["현금", "계좌이체"] else pay_method
                
                for idx, row in df_assets.iterrows():
                    if target in str(row.iloc[0]):
                        curr = to_numeric(row.iloc[1])
                        df_assets.iloc[idx, 1] = curr - amount if t_type == "지출" else curr + amount
                        break
                
                payload = {"time": now.strftime('%Y-%m-%d %H시'), "corpus": "log", "type": t_type, "cat_main": c_main, "item": item_name, "value": amount, "method": pay_method, "user": "정원"}
                if sync_sheet(payload):
                    sync_sheet({"action": "overwrite", "gid": GID_MAP["assets"], "data": [df_assets.columns.tolist()] + df_assets.values.tolist()})
                    st.success("반영 성공!"); st.rerun()

    df_a = load_data(GID_MAP["assets"])
    if not df_a.empty:
        a_rows, d_rows = [], []
        t_a, t_d = 0.0, 0.0
        
        for i, r in df_a.iterrows():
            name = str(r.iloc[0])
            qty = to_numeric(r.iloc[1])
            unit = str(r.iloc[2]) if not pd.isna(r.iloc[2]) else ""
            
            coin = re.search(r'(BTC|ETH)', name.upper())
            eval_val = qty
            is_coin = False
            if coin:
                p = get_coin_price(coin.group(1))
                if p: eval_val = qty * p; is_coin = True
            
            # 카드/대출 무조건 부채로 분류 로직
            is_debt = False
            if any(kw in name for kw in ["카드", "대출", "마이너스", "빌린"]) or eval_val < 0:
                is_debt = True
                if eval_val > 0: eval_val = -eval_val

            row = {"항목": name, "수량": float(qty), "단위": unit, "평가액": float(eval_val), "is_coin": is_coin}
            if not is_debt:
                a_rows.append(row); t_a += eval_val
            else:
                d_rows.append(row); t_d += eval_val

        # 요약 지표
        st.markdown(f"""<div style="display: flex; gap: 10px;">
            <div class="metric-card" style="flex:1;"><b>총 자산</b><br><span style="color:blue; font-size:1.5em;">{t_a:,.0f}원</span></div>
            <div class="metric-card" style="flex:1;"><b>총 부채</b><br><span style="color:red; font-size:1.5em;">{abs(t_d):,.0f}원</span></div>
            <div class="metric-card" style="flex:1; border-top: 4px solid #4dabf7;"><b>순자산</b><br><span style="font-size:1.8em; font-weight:bold;">{t_a + t_d:,.0f}원</span></div>
        </div>""", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🟢 보유 자산")
            df_pos = pd.DataFrame(a_rows)
            if not df_pos.empty:
                # 에러 방지: 데이터 타입 강제 변환
                df_pos["수량"] = df_pos["수량"].astype(float)
                df_pos["평가액"] = df_pos["평가액"].astype(float)
                st.data_editor(
                    df_pos[['항목', '수량', '단위', '평가액']],
                    use_container_width=True,
                    column_config={
                        "수량": st.column_config.NumberColumn(format="%.2f", alignment="right"),
                        "평가액": st.column_config.NumberColumn(format="%d", alignment="right")
                    },
                    key="view_assets", disabled=True
                )
        with col2:
            st.markdown("#### 🔴 부채 및 카드값")
            df_neg = pd.DataFrame(d_rows)
            if not df_neg.empty:
                df_neg["수량"] = df_neg["수량"].astype(float)
                df_neg["평가액"] = df_neg["평가액"].astype(float)
                st.data_editor(
                    df_neg[['항목', '수량', '단위', '평가액']],
                    use_container_width=True,
                    column_config={
                        "수량": st.column_config.NumberColumn(format="%d", alignment="right"),
                        "평가액": st.column_config.NumberColumn(format="%d", alignment="right")
                    },
                    key="view_debts", disabled=True
                )

        st.divider()
        st.subheader("⚙️ 자산 통합 편집기")
        ed_main = st.data_editor(df_a, num_rows="dynamic", use_container_width=True)
        if st.button("💾 자산 시트 최종 저장"):
            if sync_sheet({"action": "overwrite", "gid": GID_MAP["assets"], "data": [ed_main.columns.tolist()] + ed_main.values.tolist()}):
                st.success("시트 동기화 성공!"); st.rerun()

elif menu == "🥩 식단/재고":
    st.header("🥩 식재료 재고 및 영양 관리")
    df_i = load_data(GID_MAP["inventory"])
    if not df_i.empty:
        st.subheader("📦 재고 현황 (직접 수정 가능)")
        ed_i = st.data_editor(df_i, num_rows="dynamic", use_container_width=True)
        if st.button("💾 재고 시트 저장"):
            sync_sheet({"action":"overwrite","gid":GID_MAP["inventory"],"data":[ed_i.columns.tolist()]+ed_i.values.tolist()})
            st.success("업데이트 완료"); st.rerun()

elif menu == "📅 생활 관리":
    st.header("📅 생활 관리 및 날씨")
    t1, t2, t3 = st.tabs(["🔄 물품 교체 주기", "🗓️ 일정 관리", "☁️ 평택 날씨"])
    
    with t1:
        st.subheader("물품별 교체 주기")
        df_r = load_data(GID_MAP["replacement"])
        if not df_r.empty:
            ed_r = st.data_editor(df_r, use_container_width=True, num_rows="dynamic")
            if st.button("💾 교체 주기 저장"):
                sync_sheet({"action":"overwrite","gid":GID_MAP["replacement"],"data":[ed_r.columns.tolist()]+ed_r.values.tolist()})
                st.rerun()
        else:
            st.info("데이터가 없습니다. 시트를 확인해 주세요.")

    with t2:
        st.subheader("🗓️ 개인 구글 캘린더 연동")
        if 'cal_url' not in st.session_state:
            st.session_state.cal_url = ""
        
        cal_input = st.text_input("구글 캘린더 '이 사이트에 게시' URL 또는 iCal 주소를 입력하세요", 
                                  help="구글 캘린더 설정 -> 내 캘린더 설정 -> 캘린더 통합 -> 이 사이트에 게시 URL")
        if cal_input:
            st.session_state.cal_url = cal_input
        
        if st.session_state.cal_url:
            st.markdown(f'<iframe src="{st.session_state.cal_url}" style="border: 0" width="100%" height="600" frameborder="0" scrolling="no"></iframe>', unsafe_allow_html=True)
        else:
            st.warning("캘린더 URL을 입력하면 여기에 정원님의 일정이 나타납니다.")

    with t3:
        st.subheader("📍 평택시 실시간 날씨 상세")
        st.write(get_weather("Pyeongtaek"))

elif menu == "💊 상비약 관리":
    st.header("💊 상비약 유효기한")
    df_p = load_data(GID_MAP["pharmacy"])
    if not df_p.empty:
        # 보기용 가공
        df_view = df_p.copy()
        if len(df_view.columns) > 1: df_view = df_view.drop(df_view.columns[1], axis=1)
        df_view.iloc[:, 2] = pd.to_datetime(df_view.iloc[:, 2], errors='coerce').dt.date
        st.dataframe(df_view, use_container_width=True)
        
        st.divider()
        st.subheader("⚙️ 상비약 데이터 수정")
        ed_p = st.data_editor(df_p, num_rows="dynamic", use_container_width=True)
        if st.button("💾 상비약 저장"):
            sync_sheet({"action":"overwrite","gid":GID_MAP["pharmacy"],"data":[ed_p.columns.tolist()]+ed_p.values.tolist()})
            st.rerun()
