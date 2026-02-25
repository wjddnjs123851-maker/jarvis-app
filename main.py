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
    "replacement": "928688150" # 요청하신 GID 반영
}
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"

# --- [2. 핵심 방탄 유틸리티] ---
def to_numeric(val):
    """모든 형식의 데이터를 안전하게 숫자로 변환 (부채 마이너스 보존)"""
    if pd.isna(val) or str(val).strip() == "": return 0.0
    s = str(val).replace(',', '').replace(' ', '').strip()
    # 괄호 부채 표시 처리 (100) -> -100
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
        temp = curr['temp_C']
        desc = curr['weatherDesc'][0]['value']
        return f"🌡️ {temp}°C | {desc}"
    except: return "날씨 정보 로드 불가"

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
st.set_page_config(page_title="JARVIS Prime v83.0", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

# CSS: 인덱스 열 숨기기 및 스타일 적용
st.markdown("""
<style>
    thead tr th:first-child, tbody th { display:none; }
    .metric-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; text-align: center; margin-bottom: 15px; }
    .stTable { font-size: 0.9em; }
    /* 우측 정렬 강제 적용 */
    .text-right { text-align: right; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ 자비스 마스터")
    st.info(f"📍 평택시: {get_weather('Pyeongtaek')}")
    menu = st.radio("메뉴", ["💰 자산/가계부", "🥩 식단/재고", "📅 생활 관리", "💊 상비약 관리"])
    st.divider()

# --- [4. 메뉴별 기능 구현] ---

if menu == "💰 자산/가계부":
    st.header("📊 통합 자산 리포트 및 가계부")
    
    with st.sidebar:
        st.subheader("💸 가계부 입력")
        t_type = st.selectbox("구분", ["지출", "수입"])
        cats = ["식비", "관리비/공과금", "주거비", "통신비", "의료/건강", "교통/차량", "생활용품", "기타"]
        methods = ["현금", "계좌이체", "국민카드", "우리카드", "하나카드", "현대카드"]
        
        with st.form("log_form"):
            c_main = st.selectbox("카테고리", cats)
            item_name = st.text_input("내용")
            amount = st.number_input("금액", min_value=0, step=1000)
            pay_method = st.selectbox("결제/입금처", methods)
            
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
                    st.success("기록 및 반영 성공!"); st.rerun()

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
            
            # 카드/대출 무조건 부채로 분류
            is_debt = False
            if any(kw in name for kw in ["카드", "대출", "마이너스", "빌린"]) or eval_val < 0:
                is_debt = True
                if eval_val > 0: eval_val = -eval_val

            row = {"항목": name, "수량": float(qty), "단위": unit, "평가액": float(eval_val), "is_coin": is_coin}
            if not is_debt:
                a_rows.append(row); t_a += eval_val
            else:
                d_rows.append(row); t_d += eval_val

        st.markdown(f"""<div style="display: flex; gap: 10px;">
            <div class="metric-card" style="flex:1;"><b>총 자산</b><br><span style="color:blue; font-size:1.5em;">{t_a:,.0f}원</span></div>
            <div class="metric-card" style="flex:1;"><b>총 부채</b><br><span style="color:red; font-size:1.5em;">{abs(t_d):,.0f}원</span></div>
            <div class="metric-card" style="flex:1; border-top: 4px solid #4dabf7;"><b>순자산</b><br><span style="font-size:1.8em; font-weight:bold;">{t_a + t_d:,.0f}원</span></div>
        </div>""", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🟢 자산 (항목/수량/단위/평가액)")
            df_pos = pd.DataFrame(a_rows)
            if not df_pos.empty:
                df_pos["수량"] = pd.to_numeric(df_pos["수량"], errors='coerce').fillna(0)
                df_pos["평가액"] = pd.to_numeric(df_pos["평가액"], errors='coerce').fillna(0)
                st.data_editor(
                    df_pos[['항목', '수량', '단위', '평가액']],
                    use_container_width=True,
                    column_config={
                        "수량": st.column_config.NumberColumn(format="%.4f", alignment="right"),
                        "평가액": st.column_config.NumberColumn(format="%d", alignment="right")
                    },
                    key="view_assets", disabled=True
                )
        with col2:
            st.markdown("#### 🔴 부채 및 카드값")
            df_neg = pd.DataFrame(d_rows)
            if not df_neg.empty:
                df_neg["수량"] = pd.to_numeric(df_neg["수량"], errors='coerce').fillna(0)
                df_neg["평가액"] = pd.to_numeric(df_neg["평가액"], errors='coerce').fillna(0)
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
        st.subheader("⚙️ 자산 마스터 편집기")
        ed_main = st.data_editor(df_a, num_rows="dynamic", use_container_width=True)
        if st.button("💾 모든 변경사항 시트로 저장"):
            if sync_sheet({"action": "overwrite", "gid": GID_MAP["assets"], "data": [ed_main.columns.tolist()] + ed_main.values.tolist()}):
                st.success("시트 동기화 완료"); st.rerun()

elif menu == "🥩 식단/재고":
    st.header("🥩 식재료 재고 및 관리")
    df_i = load_data(GID_MAP["inventory"])
    if not df_i.empty:
        st.subheader("📦 현재 재고 목록")
        ed_i = st.data_editor(df_i, num_rows="dynamic", use_container_width=True)
        if st.button("💾 재고 저장"):
            sync_sheet({"action":"overwrite","gid":GID_MAP["inventory"],"data":[ed_i.columns.tolist()]+ed_i.values.tolist()})
            st.success("재고 업데이트 완료"); st.rerun()

elif menu == "📅 생활 관리":
    st.header("📅 생활 관리 센터")
    t1, t2, t3 = st.tabs(["🔄 물품 교체 주기", "🗓️ 개인 일정", "☁️ 평택시 날씨"])
    
    with t1:
        st.subheader("물품별 교체 주기 확인")
        df_r = load_data(GID_MAP["replacement"])
        if not df_r.empty:
            ed_r = st.data_editor(df_r, use_container_width=True, num_rows="dynamic")
            if st.button("💾 교체 정보 저장"):
                sync_sheet({"action":"overwrite","gid":GID_MAP["replacement"],"data":[ed_r.columns.tolist()]+ed_r.values.tolist()})
                st.rerun()
        else:
            st.info("GID 928688150 시트 데이터를 불러올 수 없습니다.")

    with t2:
        st.subheader("🗓️ 정원 님 구글 캘린더")
        cal_url = st.text_input("정원 님의 캘린더 '공개 주소' 또는 '비공개 iCal 주소'를 입력하세요", 
                                value=st.session_state.get('saved_cal_url', ''),
                                help="구글 캘린더 설정 -> 내 캘린더 설정 -> 캘린더 통합 -> 이 사이트에 게시 URL")
        if cal_url:
            st.session_state['saved_cal_url'] = cal_url
            st.markdown(f'<iframe src="{cal_url}" style="border: 0" width="100%" height="600" frameborder="0" scrolling="no"></iframe>', unsafe_allow_html=True)
        else:
            st.warning("캘린더 주소를 입력하면 정원 님의 일정이 즉시 연동됩니다.")

    with t3:
        st.subheader("📍 평택시 실시간 기상 정보")
        st.write(get_weather("Pyeongtaek"))

elif menu == "💊 상비약 관리":
    st.header("💊 상비약 유효기한")
    df_p = load_data(GID_MAP["pharmacy"])
    if not df_p.empty:
        df_v = df_p.copy()
        if len(df_v.columns) > 1: df_v = df_v.drop(df_v.columns[1], axis=1)
        df_v.iloc[:, 2] = pd.to_datetime(df_v.iloc[:, 2], errors='coerce').dt.date
        st.dataframe(df_v, use_container_width=True)
        
        st.divider()
        st.subheader("⚙️ 상비약 데이터 수정")
        ed_p = st.data_editor(df_p, num_rows="dynamic", use_container_width=True)
        if st.button("💾 상비약 저장"):
            sync_sheet({"action":"overwrite","gid":GID_MAP["pharmacy"],"data":[ed_p.columns.tolist()]+ed_p.values.tolist()})
            st.rerun()
