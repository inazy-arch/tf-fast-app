import streamlit as st
import pandas as pd
import altair as alt
import db
import utils
import time 
import json 

# ==========================================
# 1. ヘルパー関数 & 共通処理
# ==========================================

# --- 🔐 ログイン処理 ---
def login_process():
    users = db.load_users()
    uid = st.session_state.login_id
    upass = st.session_state.login_pass
    
    # バックドア (管理者用)
    if uid == "boss" and upass == "adminpass":
         st.session_state.user_info = {"id": "boss", "name": "管理者", "role": "admin", "role_title": "主将"}
         return

    if uid in users and str(users[uid]["password"]) == str(upass):
        st.session_state.user_info = users[uid]
    else:
        st.error("IDまたはパスワードが違います")

# --- 🆕 詳細表示用のポップアップ画面 (部員紹介用) ---
@st.dialog("選手詳細プロフィール")
def show_member_modal(u, users, comps):
    # ヘッダー
    st.header(f"{u['name']} ({u.get('name_kana','')})")
    
    # 基本情報
    c1, c2 = st.columns(2)
    grade_str = utils.calculate_grade(u.get("grad_year", 2026), u.get("univ_cat", "学部"))
    c1.write(f"**所属:** {u.get('affiliation','-')}")
    c2.write(f"**学年:** {grade_str}")
    
    events = u.get("events", [])
    st.write(f"**専門種目:** {', '.join(events)}")
    
    st.divider()
    
    # --- PB情報の詳細表示 ---
    st.subheader("📊 自己ベスト (PB)")
    
    # DBから全リザルト取得して、この人の分だけ抽出
    all_results = db.load_results(None)
    my_results = [r for r in all_results if str(r["user_id"]) == str(u["id"])]
    
    initial_pbs = u.get("pbs", {})
    
    if not events:
        st.info("専門種目の登録がありません")
    else:
        # 専門種目ごとに「高校PB」vs「大学PB」を表示
        for ev in events:
            rec_init = initial_pbs.get(ev, "-") # 高校PB
            
            # 大学PB (DB集計)
            rec_univ = "-"
            univ_recs = [r["result"] for r in my_results if r["event"] == ev]
            if univ_recs:
                best_so_far = univ_recs[0]
                for r in univ_recs[1:]:
                    best_so_far = utils.get_better_record(best_so_far, r, ev)
                rec_univ = best_so_far
            
            # 表示
            m1, m2, m3 = st.columns([1, 1, 1])
            m1.markdown(f"**{ev}**")
            m2.caption(f"入部前: {rec_init}")
            m3.caption(f"大学: {rec_univ}")

    st.divider()

    # --- 成長グラフ ---
    st.subheader("📈 大学での記録推移")
    if not my_results:
        st.info("まだ試合結果が登録されていません")
    else:
        df_my = pd.DataFrame(my_results)
        
        # 日付型変換
        df_my["date"] = pd.to_datetime(df_my["date"], errors="coerce")
        df_my["date"] = df_my["date"].fillna(pd.Timestamp("2000-01-01"))
        
        # 数値化
        df_my["record_val"] = df_my["result"].apply(utils.parse_record_to_float)
        df_merged = df_my.dropna(subset=["record_val"])
        
        if not df_merged.empty:
            # 種目選択
            unique_events = sorted(df_merged["event"].unique())
            graph_ev = st.selectbox("種目を選択", unique_events, key="modal_graph_sel")
            
            df_graph = df_merged[df_merged["event"] == graph_ev].copy()
            
            if not df_graph.empty:
                df_graph = df_graph.sort_values("date")
                
                chart = alt.Chart(df_graph).mark_line(point=True).encode(
                    x=alt.X('date', title='日付', axis=alt.Axis(format='%Y-%m-%d')),
                    y=alt.Y('record_val', title='記録', scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip('date', title='日付', format='%Y-%m-%d'),
                        alt.Tooltip('comp_name', title='大会名'),
                        alt.Tooltip('result', title='記録'),
                        alt.Tooltip('wind', title='風')
                    ]
                ).properties(height=250)
                st.altair_chart(chart, use_container_width=True)


# ==========================================
# 2. 各ページ関数 (Page Functions)
# ==========================================

# --- 🏠 トップページ (デザイン刷新版) ---
def page_home():
    # ヒーローセクション
    #hero_img = "https://drive.google.com/uc?export=view&id=1s0E71DgY5dcpCYqowq4UDw-KT0toiQNk"
    # 変更後 (サムネイルAPI経由・高画質指定)
    hero_img = "https://drive.google.com/thumbnail?id=1s0E71DgY5dcpCYqowq4UDw-KT0toiQNk&sz=w1920"
    #共有リンクのもとhttps://drive.google.com/file/d/1s0E71DgY5dcpCYqowq4UDw-KT0toiQNk/view?usp=sharing
    #https://drive.google.com/file/d/1s0E71DgY5dcpCYqowq4UDw-KT0toiQNk/view?usp=sharing
    
    st.markdown(f"""
    <div style="
        position: relative;
        text-align: center;
        color: white;
        background-image: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url('{hero_img}');
        background-size: cover;
        background-position: center;
        padding: 80px 20px;
        border-radius: 12px;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    ">
        <h1 style="color:white; border:none; margin:0; font-size:3rem; padding:0; text-shadow: 2px 2px 4px rgba(0,0,0,0.7);">UEC Track & Field</h1>
        <p style="font-size:1.2rem; font-weight:bold; margin-top:10px; text-shadow: 1px 1px 2px rgba(0,0,0,0.7);">電気通信大学 陸上競技部 公式ポータル</p>
    </div>
    """, unsafe_allow_html=True)

    # シンプルなナビゲーション
    c1, c2, c3 = st.columns(3)
    
    # 画面遷移ヘルパー
    def go(page):
        # app.py の st.radio の key と同じ名前に合わせる
        st.session_state["public_menu_radio"] = page 
        st.rerun()

    with c1:
        if st.button("🏃 部員紹介", use_container_width=True): go("Members")
    with c2:
        if st.button("🏆 大会結果", use_container_width=True): go("Result")
    with c3:
        if st.button("📝 ブログ", use_container_width=True): go("Blog")
    
    st.divider()

    # Newsセクション
    st.subheader("📰 Latest News")
    news_list = db.load_news()
    if not news_list:
        st.info("お知らせはありません")
    else:
        for n in news_list[:3]:
            with st.container(border=True):
                st.markdown(f"<small>{n['date']}</small>", unsafe_allow_html=True)
                st.markdown(f"**{n['title']}**")
                with st.expander("詳細を読む"):
                    st.write(n['content'])

# --- 🏃 部員紹介ページ ---
def page_members():
    st.title("🏃 部員紹介")
    
    users = db.load_users()
    comps = db.load_competitions()
    
    if not users:
        st.info("部員データがまだありません。")
        return

    # データの振り分け
    active_members = []
    obog_members = []
    for uid, u in users.items():
        if u.get("status") in ["現役", "", None]:
            active_members.append(u)
        else:
            obog_members.append(u)
    
    tab1, tab2 = st.tabs(["現役部員", "OB・OG"])
    
    # === 現役部員 ===
    with tab1:
        st.info(f"現在の部員数: {len(active_members)}名")
        
        BLOCK_MAPPING = {
            "短距離・跳躍・投擲ブロック": ["短距離", "短距離・跳躍投擲", "短距離・跳躍・投擲"],
            "中長距離ブロック 長距離パート": ["長距離"],
            "中長距離ブロック 中距離パート": ["中距離"],
            "マネージャー": ["マネージャー"]
        }
        
        grouped = {title: [] for title in BLOCK_MAPPING.keys()}
        grouped["その他/未設定"] = []
        
        for u in active_members:
            user_block = u.get("block", "")
            matched = False
            for title, keys in BLOCK_MAPPING.items():
                if user_block in keys:
                    grouped[title].append(u)
                    matched = True
                    break
            if not matched: grouped["その他/未設定"].append(u)
        
        DEFAULT_IMG = "https://placehold.co/300x300/e0e0e0/808080?text=No+Image"

        for blk_name, members in grouped.items():
            if members:
                st.markdown(f"### ▼ {blk_name}")
                cols = st.columns(3)
                for i, u in enumerate(members):
                    with cols[i % 3]:
                        with st.container(border=True):
                            img_src = u.get("image") if u.get("image") else DEFAULT_IMG
                            st.image(img_src, use_container_width=True)
                            
                            role_str = f"★{u['role_title']}" if u.get("role_title") not in ["なし", None, ""] else ""
                            st.markdown(f"**{u['name']}** {role_str}")
                            
                            grade_str = utils.calculate_grade(u.get("grad_year", 2026), u.get("univ_cat","学部"))
                            st.caption(f"{u.get('affiliation','')} {grade_str}")
                            
                            events = u.get("events", [])
                            ev_text = ", ".join(events) if events else "-"
                            st.write(f"専門: {ev_text}")
                            
                            bio = u.get("bio", "")
                            if bio:
                                st.markdown(f"<small style='color:gray;'>💬 {bio}</small>", unsafe_allow_html=True)
                            else:
                                st.caption("（ひとこと未登録）")

                            if st.button("詳細を見る", key=f"btn_detail_{u['id']}", use_container_width=True):
                                show_member_modal(u, users, comps)

    # === OB・OG ===
    with tab2:
        st.header("OB・OG 名簿")
        if not obog_members:
            st.info("OB・OGの登録はありません。")
        else:
            disp_ob = []
            for u in obog_members:
                disp_ob.append({
                    "氏名": u["name"],
                    "当時の所属": u.get("affiliation", "-"),
                    "専門種目": ", ".join(u.get("events", [])),
                    "区分": u.get("status", "OB")
                })
            st.dataframe(disp_ob, use_container_width=True)

def page_result(): 
    st.title("🏆 大会結果・ランキング")
    comps = db.load_competitions()
    users = db.load_users()
    
    tab1, tab2, tab3 = st.tabs(["📂 大会・記録会", "👑 ランキング", "🏃 選手名鑑 (グラフ)"])
    
    with tab1:
        if not comps: st.info("データがありません")
        else:
            comps.sort(key=lambda x: x['date'], reverse=True)
            comp_map = {f"{c['date']} {c['name']}": c for c in comps}
            selected_comp_name = st.selectbox("大会を選択", list(comp_map.keys()), key="res_comp_sel")
            target_comp = comp_map[selected_comp_name]
            st.markdown(f"### {target_comp['name']}")
            st.caption(f"📅 {target_comp['date']} / 📍 {target_comp['location']}")
            results = db.load_results(target_comp['id'])
            if not results: st.warning("結果はまだ登録されていません")
            else:
                df = pd.DataFrame(results)
                events = sorted(df["event"].unique())
                for ev in events:
                    with st.expander(f"{ev}", expanded=True):
                        df_ev = df[df["event"] == ev].copy()
                        cols_map = {"round": "ラウンド", "heat": "組", "lane": "レーン", "user_name": "氏名", "result": "記録", "wind": "風", "rank": "順位", "comment": "備考"}
                        disp_cols = [c for c in cols_map.keys() if c in df_ev.columns]
                        df_show = df_ev[disp_cols].rename(columns=cols_map)
                        st.dataframe(df_show, hide_index=True, use_container_width=True)

    with tab2:
        st.subheader("種目別ランキング (Top 5)")
        all_results = db.load_results(None)
        if not all_results: st.info("データがありません")
        else:
            df_all = pd.DataFrame(all_results)
            event_list = sorted(df_all["event"].unique())
            target_event = st.selectbox("種目を選択", event_list, key="rank_ev_sel")
            df_rank = df_all[df_all["event"] == target_event].copy()
            df_rank["record_val"] = df_rank["result"].apply(utils.parse_record_to_float)
            df_rank = df_rank.dropna(subset=["record_val"])
            
            # トラックかフィールドかでソート順を変える
            is_track = utils.is_track_event(target_event)
            df_rank = df_rank.sort_values("record_val", ascending=is_track)
            
            top5 = df_rank.head(5).reset_index(drop=True)
            top5.index += 1
            st.table(top5[["user_name", "result", "wind", "comp_id"]])

    # === tab3: 選手名鑑 (グラフ) の修正版 ===
    with tab3:
        st.subheader("選手個人データ")
        if not users: st.warning("選手データがまだ登録されていません。")
        else:
            # 辞書のキーと値を逆転させて名前で引けるようにする
            user_names = {u["name"]: uid for uid, u in users.items()}
            
            if not user_names: st.warning("表示可能な選手がいません。")
            else:
                target_user_name = st.selectbox("選手を検索", list(user_names.keys()), key="pl_sel")
                
                if target_user_name:
                    target_uid = user_names[target_user_name]
                    u_info = users[target_uid]
                    
                    # プロフィール表示
                    st.write(f"**所属:** {u_info.get('affiliation','-')} / **学年:** {utils.calculate_grade(u_info.get('grad_year', 2026), u_info.get('univ_cat','学部'))}")
                    st.write(f"**専門:** {', '.join(u_info.get('events',[]))}")
                    
                    # 全リザルトから本人の分を抽出
                    all_res = db.load_results(None)
                    my_res = [r for r in all_res if str(r["user_id"]) == str(target_uid)]
                    
                    if not my_res:
                        st.info("出場記録がありません")
                    else:
                        # ★★★ 修正: mergeは不要！そのまま使う ★★★
                        df_my = pd.DataFrame(my_res)
                        
                        # 日付型に変換 (ここが重要)
                        df_my["date"] = pd.to_datetime(df_my["date"], errors="coerce")
                        df_my["date"] = df_my["date"].fillna(pd.Timestamp("2000-01-01"))
                        
                        # グラフ描画
                        if "event" in df_my.columns:
                            # 種目リスト作成
                            my_events = sorted(df_my["event"].unique())
                            graph_event = st.selectbox("グラフ表示する種目", my_events, key="gr_ev_sel")
                            
                            # その種目のデータだけにする
                            df_graph = df_my[df_my["event"] == graph_event].copy()
                            
                            # 記録を数値化
                            df_graph["record_val"] = df_graph["result"].apply(utils.parse_record_to_float)
                            df_graph = df_graph.dropna(subset=["record_val"])
                            
                            if not df_graph.empty:
                                # 日付順に並べ替え
                                df_graph = df_graph.sort_values("date")
                                
                                # Altairでグラフ描画
                                chart = alt.Chart(df_graph).mark_line(point=True).encode(
                                    x=alt.X('date', title='日付', axis=alt.Axis(format='%Y-%m-%d')),
                                    y=alt.Y('record_val', title='記録', scale=alt.Scale(zero=False)),
                                    tooltip=[
                                        alt.Tooltip('date', title='日付', format='%Y-%m-%d'),
                                        alt.Tooltip('comp_name', title='大会名'),
                                        alt.Tooltip('result', title='記録'),
                                        alt.Tooltip('wind', title='風')
                                    ]
                                ).properties(height=300)
                                st.altair_chart(chart, use_container_width=True)
                            else:
                                st.caption("※グラフ描画可能な数値データがありません")
                        
                        # 履歴一覧表示
                        st.caption("競技履歴")
                        # 表示したい列
                        disp_cols = ["date", "comp_name", "event", "result", "wind", "rank", "comment"]
                        # 実際に存在する列だけ選ぶ
                        existing_cols = [c for c in disp_cols if c in df_my.columns]
                        
                        # 表示用データ作成
                        df_disp = df_my[existing_cols].sort_values("date", ascending=False).copy()
                        # 日付を綺麗に文字列に戻す
                        df_disp["date"] = df_disp["date"].dt.strftime("%Y-%m-%d")
                        
                        st.dataframe(df_disp, hide_index=True, use_container_width=True)

# --- 📝 ブログページ ---
def page_blog():
    st.title("🏃 部員ブログ")
    st.info("部員による練習日誌や日常のブログです。")
    
    blogs = db.load_blogs()
    if not blogs:
        st.write("まだ投稿がありません")
        return
        
    for b in blogs:
        with st.container(border=True):
            c1, c2 = st.columns([1, 4])
            with c1:
                st.caption(f"🖊 {b.get('author_name', '選手')}")
                st.caption(b.get('created_at', ''))
            with c2:
                st.subheader(b.get('title', '無題'))
                if b.get('image'):
                    st.image(b['image'], use_container_width=True)
                st.write(b.get('content', ''))

# --- その他のページ ---
def page_obog(): 
    st.title("OBOG")
    st.write("OB・OG会ページ")

def page_link(): 
    st.title("Link")
    st.write("リンク集")

def page_login():
    st.title("部員ログイン")
    with st.form("login_form"):
        st.text_input("ユーザーID", key="login_id")
        st.text_input("パスワード", type="password", key="login_pass")
        st.form_submit_button("ログイン", on_click=login_process)