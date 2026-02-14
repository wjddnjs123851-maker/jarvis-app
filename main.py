import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "0", "Finance": "0", "Assets": "0"} 

FIXED_DATA = {
    "health_target": {"칼로리": 2000, "지방": 65, "콜레스테롤": 300, "나트륨": 2000, "탄수화물": 300, "식이섬유": 30, "당": 50, "단백질": 150},
    "stocks": {
        "동성화인텍": {"평단": 22701, "수량": 21, "코드": "033500"},
        "삼성중공업": {"평단": 16761, "수량": 88, "코드": "010140"},
        "SK하이닉스": {"평단": 473521, "수량": 6, "코드": "000660"},
        "삼성전자": {"평단": 78895, "수량": 46, "코드": "005930"}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400, "마켓": "KRW-BTC"},
        "ETH": {"평단": 4243000, "수량": 0.03417393, "마켓": "KRW-ETH"}
    },
    "recurring": [
        {"항목": "임대료", "금액": 261620}, {"항목": "대출 이자", "금액": 263280},
        {"항목": "통신비", "금액": 136200}, {"항목": "보험료", "금액": 121780},
        {"항목": "청년도약계좌(적금)", "금액": 700000}, {"항목": "구독서비스", "금액": 42680}
    ],
    "categories": {
        "지출": ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타지출"],
        "수입": ["급여", "금융소득", "기타"],
        "자산이동": ["적금/청약 납입", "주식/코인 매수", "대출 원금상환"]
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, "칫솔": {"last": "2026-02-06", "period": 90}, "이불세탁": {"last": "2026-02-04", "period": 14}
    }
}

API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# --- [2. 유틸리티 함수] ---
def format_krw(val):
    try: return f"{int(float(str(val).replace(',', '').replace('원', ''))):,}원"
    except: return "0원"

def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try: requests.post(API_URL, data=json.dumps(payload), timeout=5); return True
    except: return False

@st.cache_data(ttl=10)
def load_sheet_safe(sheet_name):
    gid = GID_MAP.get(sheet_name, "0")
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def get_live_prices():
    prices = {"stocks": {}, "crypto": {}, "gold": 231345}
    for n, i in FIXED_DATA["stocks"].items():
        try:
            res = requests.get(f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{i['코드']}", timeout=1).json()
            prices["stocks"][n] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][n] = i['평단']
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=1).json()
        for c in res: prices["crypto"][c['market']] = float(c['trade_price'])
    except:
        for k, v in FIXED_DATA["crypto"].items(): prices["crypto"][v['마켓']] = v['평단']
    return prices

# --- [3. 메인 레이아웃 및 스타일] ---
st.set_page_config(page_title="JARVIS v27.0", layout="wide")
st.markdown("<style>.stTable td { text-align: right !important; }</style>", unsafe_allow_html=True)

if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in FIXED_DATA["health_target"].keys()}

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["영양/식단/체중", "자산/투자/가계부", "재고/생활관리"])
    st.divider()
    
    if menu == "영양/식단/체중":
        st.subheader("영양 및 체중 입력")
        in_w = st.number_input("체중 (kg)", 0.0, 150.0, 125.0, step=0.1)
        # 보스 요청 순서: 지방 -> 콜레스테롤 -> 나트륨 -> 탄수 -> 식이섬유 -> 당 -> 단백
        in_kcal = st.number_input("칼로리 (kcal)", 0)
        in_fat = st.number_input("지방 (g)", 0)
        in_chol = st.number_input("콜레스테롤 (mg)", 0)
        in_na = st.number_input("나트륨 (mg)", 0)
        in_carb = st.number_input("탄수화물 (g)", 0)
        in_fiber = st.number_input("식이섬유 (g)", 0)
        in_sugar = st.number_input("당 (g)", 0)
        in_prot = st.number_input("단백질 (g)", 0)
        
        if st.button("데이터 통합 전송"):
            send_to_sheet("건강", "체중", in_w)
            for k, v in zip(FIXED_DATA["health_target"].keys(), [in_kcal, in_fat, in_chol, in_na, in_carb, in_fiber, in_sugar, in_prot]):
                send_to_sheet("건강", k, v)
                st.session_state.consumed[k] += v
            st.success("전송 완료!")

    elif menu == "자산/투자/가계부":
        st.subheader("가계부 기록")
        t_type = st.selectbox("구분", ["지출", "수입", "자산이동"])
        t_cat = st.selectbox("카테고리", FIXED_DATA["categories"][t_type])
        t_memo = st.text_input("상세 메모")
        t_val = st.number_input("금액", 0)
        if st.button("시트 기록"):
            if send_to_sheet(t_type, f"{t_cat} - {t_memo}", t_val): st.success("기록 완료")

# --- [4. 메뉴별 대시보드 출력] ---
st.title(f"자비스 리포트: {menu}")

if menu == "영양/식단/체중":
    st.subheader("오늘의 영양 섭취 현황")
    n_rows = [{"영양소": k, "현재": v, "목표": FIXED_DATA["health_target"][k]} for k, v in st.session_state.consumed.items()]
    df_n = pd.DataFrame(n_rows)
    df_n.index = range(1, len(df_n) + 1)
    st.table(df_n)

elif menu == "자산/투자/가계부":
    live = get_live_prices()
    st.subheader("매달 고정 지출")
    df_recur = pd.DataFrame(FIXED_DATA["recurring"])
    df_recur["금액"] = df_recur["금액"].apply(format_krw)
    st.table(df_recur.assign(No=range(1, len(df_recur)+1)).set_index('No'))
    
    st.subheader("통합 자산 관리")
    df_assets_raw = load_sheet_safe("Assets")
    a_rows = []
    
    # 💡 데이터 밀림 방지 로직 강화
    if not df_assets_raw.empty:
        for _, row in df_assets_raw.iterrows():
            try:
                name = str(row.iloc[0])
                if "항목" in name or "2026" in name: continue # 제목줄이나 날짜 오독 방지
                a_rows.append({"분류": "금융", "항목": name, "평가액": format_krw(row.iloc[1]), "비고": "기초잔액"})
            except: continue
            
    # 주식/코인 데이터 (FIXED_DATA 기반 강제 정렬)
    for n, i in FIXED_DATA["stocks"].items():
        curr = live["stocks"].get(n, i['평단'])
        a_rows.append({"분류": "주식", "항목": n, "평가액": format_krw(curr * i['수량']), "비고": f"{((curr/i['평단'])-1)*100:.2f}%"})
    
    for n, i in FIXED_DATA["crypto"].items():
        curr = live["crypto"].get(i['마켓'], i['평단'])
        a_rows.append({"분류": "코인", "항목": n, "평가액": format_krw(int(curr * i['수량'])), "비고": f"{((curr/i['평단'])-1)*100:.2f}%"})

    df_final = pd.DataFrame(a_rows)
    df_final.index = range(1, len(df_final) + 1)
    st.table(df_final)
