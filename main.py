# --- [탭 1] 투자 & 자산 ---
if menu == "투자 & 자산":
    # ----------------------------------------------------
    # SECTION 1: 종합 자산 현황 (Stock)
    # ----------------------------------------------------
    st.header("💎 종합 자산 관리 (Net Worth)")
    
    try:
        df_assets = load_sheet_data(GID_MAP["Assets"])
        df_log = load_sheet_data(GID_MAP["Log"])
        
        # 1. Assets 데이터 가공
        if not df_assets.empty and len(df_assets.columns) >= 2:
            df_assets = df_assets.iloc[:, :2]
            df_assets.columns = ["항목", "금액"]
            df_assets["val"] = df_assets["금액"].apply(to_numeric)
        else: df_assets = pd.DataFrame(columns=["항목", "금액", "val"])

        # 2. Log 데이터 가공 (가계부 2.0 구조)
        df_clean = pd.DataFrame()
        if not df_log.empty:
            if len(df_log.columns) >= 6: df_clean = df_log.iloc[:, [0, 1, 2, 4, 5]] # 날짜,구분,대분류,내용,금액
            else: df_clean = df_log.iloc[:, :5] # fallback
            
            df_clean.columns = ["날짜", "구분", "카테고리", "내용", "수치"]
            df_clean['날짜'] = pd.to_datetime(df_clean['날짜'].astype(str).str.replace('.', '-'), errors='coerce')
            df_clean['val'] = df_clean['수치'].apply(to_numeric)
            df_clean = df_clean.dropna(subset=['날짜'])

        # 3. 자산 계산 (현금흐름 반영 생략 - Assets 시트가 최신이라 가정)
        # 단, 카드값 등 부채 자동계산이 필요하면 여기서 로직 추가 가능
        
        # 주식/코인 병합
        inv_rows = []
        for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
            for name, info in items.items(): inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})
        
        df_total = pd.concat([df_assets, pd.DataFrame(inv_rows)], ignore_index=True)
        
        a_df = df_total[df_total["val"] >= 0].copy()
        l_df = df_total[df_total["val"] < 0].copy()
        net_worth = a_df["val"].sum() - abs(l_df["val"].sum())

        # [자산 섹션 UI]
        col_a, col_l, col_n = st.columns([1, 1, 0.8])
        with col_a:
            st.subheader("🔹 자산 (Assets)")
            st.metric("총 자산", format_krw(a_df["val"].sum()))
            if not a_df.empty:
                d_a = a_df[["항목", "val"]].copy()
                d_a["금액"] = d_a["val"].apply(format_krw)
                st.dataframe(d_a[["항목", "금액"]], column_config={"금액": st.column_config.NumberColumn(format="%d원")}, use_container_width=True, hide_index=True)
        
        with col_l:
            st.subheader("🔸 부채 (Liabilities)")
            st.metric("총 부채", format_krw(l_df["val"].sum()))
            if not l_df.empty:
                d_l = l_df[["항목", "val"]].copy()
                d_l["금액"] = d_l["val"].apply(lambda x: format_krw(abs(x)))
                st.dataframe(d_l[["항목", "금액"]], column_config={"금액": st.column_config.NumberColumn(format="%d원")}, use_container_width=True, hide_index=True)
            else: st.success("부채 없음")
            
        with col_n:
            st.markdown(f"<div style='background-color:#1c1e26; padding:15px; border-radius:10px; text-align:center; border: 1px solid {COLOR_GOOD};'>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin:0; color:gray;'>순자산</h3>", unsafe_allow_html=True)
            st.markdown(f"<h1 style='margin:0; color:{COLOR_GOOD};'>{format_krw(net_worth)}</h1>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        # ----------------------------------------------------
        # SECTION 2: 월별 수입/지출 분석 (Flow)
        # ----------------------------------------------------
        st.header("📊 월별 지출 분석 (Monthly Flow)")
        
        if not df_clean.empty:
            # 월 선택 기능
            df_clean['년월'] = df_clean['날짜'].dt.strftime('%Y-%m')
            month_list = sorted(df_clean['년월'].unique(), reverse=True)
            
            # 데이터가 2026-02 이후인 것만 필터 (원하면 제거 가능)
            month_list = [m for m in month_list if m >= "2026-02"]
            
            if not month_list:
                st.info("📉 2026년 2월 이후의 데이터가 없습니다.")
            else:
                sel_month = st.selectbox("분석할 월을 선택하세요", month_list)
                
                # 해당 월 데이터 필터링
                m_df = df_clean[df_clean['년월'] == sel_month].copy()
                
                # 통계 계산
                inc_sum = m_df[m_df['구분'] == '수입']['val'].sum()
                exp_sum = m_df[m_df['구분'] == '지출']['val'].sum()
                balance = inc_sum - exp_sum
                
                # 1. 핵심 지표 (Metrics)
                m1, m2, m3 = st.columns(3)
                m1.metric("총 수입", format_krw(inc_sum), delta="Income", delta_color="normal")
                m2.metric("총 지출", format_krw(exp_sum), delta="-Expense", delta_color="inverse")
                m3.metric("월 수지 (Balance)", format_krw(balance), delta=f"{'흑자' if balance >=0 else '적자'}")
                
                # 2. 지출 카테고리별 차트
                st.subheader(f"{sel_month} 지출 카테고리별 통계")
                exp_df = m_df[m_df['구분'] == '지출']
                
                if not exp_df.empty:
                    cat_group = exp_df.groupby("카테고리")["val"].sum().sort_values(ascending=False)
                    
                    c_chart, c_detail = st.columns([6, 4])
                    
                    with c_chart:
                        # 막대 그래프 (주황색)
                        st.bar_chart(cat_group, color=COLOR_BAD, height=300)
                    
                    with c_detail:
                        # 상세 표
                        cat_df = cat_group.reset_index()
                        cat_df.columns = ["카테고리", "금액"]
                        cat_df["비중"] = (cat_df["금액"] / exp_sum * 100).apply(lambda x: f"{x:.1f}%")
                        cat_df["금액"] = cat_df["금액"].apply(format_krw)
                        st.dataframe(cat_df, hide_index=True, use_container_width=True)
                else:
                    st.info("이 달의 지출 내역이 없습니다.")
                    
        else:
            st.info("Log 시트에 데이터가 입력되면 이곳에 월별 통계가 나타납니다.")

    except Exception as e: st.error(f"⚠️ 에러: {e}")

# --- [탭 2] 식단 & 건강 ---
elif menu == "식단 & 건강":
    st.header("🥗 실시간 영양 분석 리포트")
    # ... (기존과 동일, 길이 관계상 생략하지 않고 유지해야 하지만, 요청에 의해 기존 코드는 유지됨을 가정)
    # 실제 사용 시에는 Part 2의 나머지 부분(식단, 재고관리)도 꼭 붙여넣으셔야 합니다.
    # 안전을 위해 식단/재고관리 코드도 아래에 이어서 드립니다.

    try: d_day = (datetime(2026, 5, 30) - datetime.now()).days
    except: d_day = 0
    st.info(f"💍 결혼식까지 D-{d_day} | 현재 체중 125.00kg 기준 감량 모드")

    col_input, col_summary = st.columns([6, 4])
    with col_input:
        st.subheader("📝 영양 성분 상세 기록")
        with st.form("full_input"):
            in_w = st.number_input("오늘 체중 (kg)", 0.0, 200.0, 125.0, step=0.1)
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                in_kcal = st.number_input("칼로리 (kcal)", 0.0, step=10.0)
                in_carb = st.number_input("탄수화물 (g)", 0.0, step=1.0)
                in_sugar = st.number_input("당류 (g)", 0.0, step=1.0)
                in_na = st.number_input("나트륨 (mg)", 0.0, step=10.0)
            with c2:
                in_prot = st.number_input("단백질 (g)", 0.0, step=1.0)
                in_fat = st.number_input("지방 (g)", 0.0, step=1.0)
                in_fiber = st.number_input("식이섬유 (g)", 0.0, step=1.0)
                in_chol = st.number_input("콜레스테롤 (mg)", 0.0, step=10.0)
            st.write("")
            if st.form_submit_button("✅ 저장", use_container_width=True):
                if in_w > 0 and in_w != 125.0: send_to_sheet("건강", "체중", in_w, corpus="Health")
                nutri_map = {"칼로리": in_kcal, "탄수화물": in_carb, "단백질": in_prot, "지방": in_fat, "당": in_sugar, "식이섬유": in_fiber, "나트륨": in_na, "콜레스테롤": in_chol}
                cnt = 0
                for k, v in nutri_map.items():
                    if v > 0: send_to_sheet("식단", k, v, corpus="Health"); cnt += 1
                if cnt > 0: st.success("저장 완료"); st.rerun()
    with col_summary:
        st.subheader("📊 오늘의 요약")
        cur_nutri = {k: 0 for k in DAILY_GUIDE.keys()}
        today_str = datetime.now().strftime('%Y-%m-%d')
        cur_kcal = 0
        try:
            df_log = load_sheet_data(GID_MAP["Log"])
            if not df_log.empty:
                # Log 컬럼 매핑 안전장치
                if len(df_log.columns) >= 6: 
                    temp = df_log.iloc[:, [0, 1, 4, 5]]
                    temp.columns = ["날짜", "구분", "항목", "수치"]
                else: 
                    temp = df_log.iloc[:, :4]
                    temp.columns = ["날짜", "구분", "항목", "수치"]

                temp['날짜'] = temp['날짜'].astype(str).str.replace('.', '-')
                df_today = temp[temp['날짜'].str.contains(today_str, na=False)]
                
                for k in cur_nutri.keys():
                    cur_nutri[k] = df_today[(df_today['구분']=='식단') & (df_today['항목']==k)]['수치'].apply(to_numeric).sum()
                cur_kcal = cur_nutri["칼로리"]
        except: pass
        
        rem = DAILY_GUIDE["칼로리"]["val"] - cur_kcal
        st.metric("남은 칼로리", f"{rem:.0f} kcal", delta=f"-{cur_kcal:.0f} 섭취")
        st.progress(min(cur_kcal / DAILY_GUIDE["칼로리"]["val"], 1.0))
        st.divider()
        nc1, nc2 = st.columns(2)
        n_list = list(DAILY_GUIDE.keys()); n_list.remove("칼로리")
        for i, name in enumerate(n_list):
            val = cur_nutri[name]
            guide = DAILY_GUIDE[name]
            col = nc1 if i % 2 == 0 else nc2
            with col:
                st.caption(name)
                st.progress(min(val / guide['val'], 1.0))
                st.write(f"{val:.0f}/{guide['val']}{guide['unit']}")

# --- [탭 3] 재고 관리 ---
elif menu == "재고 관리":
    st.header("📦 식자재 및 생활용품 관리")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("🛒 식재료 현황")
        if 'inventory' not in st.session_state:
            st.session_state.inventory = pd.DataFrame([
                {"항목": "냉동 삼치", "수량": "4팩", "유통기한": "2026-05-10"}, {"항목": "냉동닭다리살", "수량": "3팩", "유통기한": "2026-06-01"},
                {"항목": "단백질 쉐이크", "수량": "9개", "유통기한": "2026-12-30"}, {"항목": "카무트/쌀 혼합", "수량": "2kg", "유통기한": "2026-10-20"},
                {"항목": "파스타면", "수량": "대량", "유통기한": "-"}, {"항목": "소면", "수량": "1봉", "유통기한": "-"},
                {"항목": "쿠스쿠스", "수량": "500g", "유통기한": "2027-01-01"}, {"항목": "우동사리", "수량": "3봉", "유통기한": "-"},
                {"항목": "라면", "수량": "6봉", "유통기한": "-"}, {"항목": "토마토 페이스트", "수량": "10캔", "유통기한": "2027-05-15"},
                {"항목": "나시고랭 소스", "수량": "1팩", "유통기한": "2026-11-20"}, {"항목": "치아씨드/아사이베리", "수량": "보유", "유통기한": "-"},
                {"항목": "김치 4종", "수량": "보유", "유통기한": "-"}, {"항목": "당근", "수량": "보유", "유통기한": "-"}, {"항목": "감자", "수량": "보유", "유통기한": "-"}
            ])
        st.session_state.inventory = st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True, key="inv")
    with c2:
        st.subheader("⏰ 생활용품 교체")
        if 'supplies' not in st.session_state:
            st.session_state.supplies = pd.DataFrame([
                {"품목": "칫솔(정원)", "최근교체일": "2026-01-15", "주기": 30}, {"품목": "칫솔(서진)", "최근교체일": "2026-02-15", "주기": 30},
                {"품목": "면도날", "최근교체일": "2026-02-01", "주기": 14}, {"품목": "수세미", "최근교체일": "2026-02-15", "주기": 30},
                {"품목": "정수기필터", "최근교체일": "2025-12-10", "주기": 120}
            ])
        st.session_state.supplies = st.data_editor(st.session_state.supplies, num_rows="dynamic", use_container_width=True, key="sup")
        try:
            cdf = st.session_state.supplies.copy()
            if '주기(일)' in cdf.columns: cdf.rename(columns={'주기(일)': '주기'}, inplace=True)
            if '주기' not in cdf.columns: cdf['주기'] = 30
            cdf['최근교체일'] = pd.to_datetime(cdf['최근교체일'], errors='coerce')
            cdf['교체예정일'] = cdf.apply(lambda x: x['최근교체일'] + pd.Timedelta(days=int(x['주기'])) if pd.notnull(x['최근교체일']) else pd.NaT, axis=1)
            st.caption("📅 교체 예정일 (자동 계산)")
            st.dataframe(cdf[['품목', '교체예정일']].assign(교체예정일=cdf['교체예정일'].dt.strftime('%Y-%m-%d').fillna("-")).set_index('품목'), use_container_width=True)
        except: pass
