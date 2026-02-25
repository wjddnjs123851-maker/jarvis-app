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
    "replacement": "928688150" 
}
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"

# --- [2. 핵심 방탄 유틸리티] ---
def to_numeric_safe(val):
    """모든 데이터 타입을 숫자로 강제 정제 (에러 방지 핵심)"""
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
        return f"🌡️ {curr['temp_C']}°C | {curr['weatherDesc'][0]['value']}"
    except: return "날씨 로드 불가"

def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url).dropna(how='all')
        # 정원 님 명령: 모든 메뉴에서 '순번' 및 'Index' 열은 무조건 삭제
        cols_to_drop = [c for c in df.columns if '순번' in str(c) or 'Unnamed' in str(c) or 'index' in str(c).lower()]
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)
        return df
    except: return pd.DataFrame()

def sync_sheet(payload):
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

# --- [3. UI 설정] ---
st.set_page_config(page_title="JARVIS Prime v91.0", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

# CSS: 인덱스 열 완전 숨기기 (더 이상 순번은 없습니다)
st.markdown("""
<style>
    thead tr th:first-child, tbody th { display:none; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    .metric-card { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; text-align: center; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ 자비스 마스터")
    st.info(f"📍 평택시 날씨: {get_weather('Pyeongtaek')}")
    menu = st.radio("메뉴", ["💰 자산 & 가계부", "🥩 식단 & 재고", "📅 생활 & 일정", "💊 상비약 관리"])
    st.divider()

# --- [4. 메뉴별 기능 구현] ---

if menu == "💰 자산 & 가계부":
    st.header("📊 통합 자산 리포트 및 관리")
    
    with st.sidebar:
        st.subheader("💸 가계부 입력")
        t_type = st.selectbox("구분", ["지출", "수입"])
        cats = ["식비", "주거/통신", "생활용품", "의료/건강", "교통/차량", "기타"]
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
                        curr = to_numeric_safe(row.iloc[1])
                        df_assets.iloc[idx, 1] = curr - amount if t_type == "지출" else curr + amount
                        break
                
                payload = {"time": now.strftime('%Y-%m-%d %H시'), "corpus": "log", "type": t_type, "cat_main": c_main, "item": item_name, "value": amount, "method": pay_method, "user": "정원"}
                if sync_sheet(payload):
                    sync_sheet({"action": "overwrite", "gid": GID_MAP["assets"], "data": [df_assets.columns.tolist()] + df_assets.values.tolist()})
                    st.success("기록 및 반영 완료"); st.rerun()

    df_a = load_data(GID_MAP["assets"])
    if not df_a.empty:
        # 데이터 정제 (에러 방지 핵심)
        df_a.iloc[:, 1] = pd.to_numeric(df_a.iloc[:, 1], errors='coerce').fillna(0.0).astype(float)
        
        a_rows, d_rows = [], []
        t_a, t_d = 0.0, 0.0
        
        for i, r in df_a.iterrows():
            name = str(r.iloc[0])
            qty = float(r.iloc[1])
            unit = str(r.iloc[2]) if not pd.isna(r.iloc[2]) else ""
            note = str(r.iloc[3]) if not pd.isna(r.iloc[3]) else ""
            
            coin = re.search(r'(BTC|ETH)', name.upper())
            eval_val = qty
            is_coin = False
            if coin:
                p = get_coin_price(coin.group(1))
                if p: eval_val = qty * p; is_coin = True
            
            # 부채 분류 (카드, 대출)
            is_debt = False
            if any(kw in name for kw in ["카드", "대출", "마이너스", "빌린"]) or eval_val < 0:
                is_debt = True
                if eval_val > 0: eval_val = -eval_val

            row = {"항목": name, "수량": qty, "단위": unit, "평가액": eval_val, "비고": note, "is_coin": is_coin}
            if not is_debt:
                a_rows.append(row); t_a += eval_val
            else:
                d_rows.append(row); t_d += eval_val

        # 요약 카드
        st.markdown(f"""<div style="display: flex; gap: 10px;">
            <div class="metric-card" style="flex:1;"><b>총 자산</b><br><span style="color:blue; font-size:1.5em;">{t_a:,.0f}원</span></div>
            <div class="metric-card" style="flex:1;"><b>총 부채</b><br><span style="color:red; font-size:1.5em;">{abs(t_d):,.0f}원</span></div>
            <div class="metric-card" style="flex:1; border-top: 4px solid #4dabf7;"><b>순자산</b><br><span style="font-size:1.8em; font-weight:bold;">{t_a + t_d:,.0f}원</span></div>
        </div>""", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🟢 자산 현황 (직접 편집)")
            df_pos = pd.DataFrame(a_rows)
            if not df_pos.empty:
                # 에러 방지용 타입 고정
                df_pos = df_pos.astype({"수량": float, "평가액": float})
                ed_pos = st.data_editor(
                    df_pos[['항목', '수량', '단위', '평가액', '비고']],
                    use_container_width=True,
                    column_config={
                        "수량": st.column_config.NumberColumn(format="%.4f", alignment="right"),
                        "평가액": st.column_config.NumberColumn(format="%d", alignment="right", disabled=True)
                    },
                    key="assets_top_editor", hide_index=True
                )
        with col2:
            st.markdown("#### 🔴 부채 및 카드값 (직접 편집)")
            df_neg = pd.DataFrame(d_rows)
            if not df_neg.empty:
                df_neg = df_neg.astype({"수량": float, "평가액": float})
                ed_neg = st.data_editor(
                    df_neg[['항목', '수량', '단위', '평가액', '비고']],
                    use_container_width=True,
                    column_config={
                        "수량": st.column_config.NumberColumn(format="%d", alignment="right"),
                        "평가액": st.column_config.NumberColumn(format="%d", alignment="right", disabled=True)
                    },
                    key="debts_top_editor", hide_index=True
                )

        if st.button("💾 위 수정사항을 구글 시트에 최종 저장"):
            combined = []
            for d in [ed_pos, ed_neg]:
                for _, row in d.iterrows():
                    combined.append([row['항목'], row['수량'], row['단위'], row['비고']])
            if sync_sheet({"action": "overwrite", "gid": GID_MAP["assets"], "data": [df_a.columns.tolist()] + combined}):
                st.success("자산 데이터가 저장되었습니다."); st.rerun()

elif menu == "🥩 식단 & 재고":
    st.header("🥩 식재료 재고 및 편집")
    df_i = load_data(GID_MAP["inventory"])
    if not df_i.empty:
        # 수치 열 정제
        for col in df_i.columns:
            if any(kw in col for kw in ['수량', '개수', '중량']):
                df_i[col] = pd.to_numeric(df_i[col], errors='coerce').fillna(0.0)
        
        st.subheader("📦 재고 목록 (직접 편집)")
        ed_i = st.data_editor(df_i, num_rows="dynamic", use_container_width=True, key="inventory_editor", hide_index=True)
        if st.button("💾 재고 시트 저장"):
            sync_sheet({"action":"overwrite","gid":GID_MAP["inventory"],"data":[ed_i.columns.tolist()]+ed_i.values.tolist()})
            st.success("재고가 업데이트되었습니다."); st.rerun()

elif menu == "📅 생활 & 일정":
    st.header("📅 생활 관리 허브")
    t1, t2, t3 = st.tabs(["🔄 물품 교체 주기", "🗓️ 개인 일정", "☁️ 평택시 날씨"])
    
    with t1:
        st.subheader("🔄 물품 교체 관리 (GID: 928688150)")
        df_r = load_data(GID_MAP["replacement"])
        if not df_r.empty:
            ed_r = st.data_editor(df_r, use_container_width=True, num_rows="dynamic", key="replacement_editor", hide_index=True)
            if st.button("💾 교체 정보 저장"):
                sync_sheet({"action":"overwrite","gid":GID_MAP["replacement"],"data":[ed_r.columns.tolist()]+ed_r.values.tolist()})
                st.success("정보가 저장되었습니다."); st.rerun()

    with t2:
        st.subheader("🗓️ 개인 구글 캘린더")
        cal_url = st.text_input("개인 구글 캘린더 URL을 입력하세요", value=st.session_state.get('saved_cal_url', ''))
        if cal_url:
            st.session_state['saved_cal_url'] = cal_url
            st.markdown(f'<iframe src="{cal_url}" style="border: 0" width="100%" height="600" frameborder="0" scrolling="no"></iframe>', unsafe_allow_html=True)

    with t3:
        st.subheader("📍 평택시 실시간 날씨 정보")
        st.write(get_weather("Pyeongtaek"))

elif menu == "💊 상비약 관리":
    st.header("💊 상비약 관리 및 편집")
    df_p = load_data(GID_MAP["pharmacy"])
    if not df_p.empty:
        st.subheader("💊 상비약 목록 (직접 편집)")
        ed_p = st.data_editor(df_p, num_rows="dynamic", use_container_width=True, key="pharmacy_editor", hide_index=True)
        if st.button("💾 상비약 데이터 저장"):
            sync_sheet({"action":"overwrite","gid":GID_MAP["pharmacy"],"data":[ed_p.columns.tolist()]+ed_p.values.tolist()})
            st.success("상비약 현황이 저장되었습니다."); st.rerun()
