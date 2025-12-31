import streamlit as st
import json
import time
import pandas as pd
import db
import utils
import random
import string
import re
from datetime import datetime, date

def page_competition_reg():
    st.title("🏆 新規大会登録 (競技会)")
    with st.form("comp_reg"):
        name = st.text_input("大会名")
        date_val = st.date_input("開催日")
        deadline = st.date_input("締切")
        loc = st.text_input("場所")
        
        st.markdown("---")
        st.write("⏱️ **資格記録の有効期間設定**")
        use_period = st.checkbox("有効期間を指定する（例: シーズンベストのみ）", value=False)
        
        c1, c2 = st.columns(2)
        if use_period:
            this_year = date.today().year
            valid_start = c1.date_input("開始日", value=date(this_year, 1, 1))
            valid_end = c2.date_input("終了日", value=date_val)
        else:
            valid_start = None
            valid_end = None
            st.caption("※ 指定しない場合、過去すべての期間のベスト記録(PB)が参照されます。")
            
        st.markdown("---")
        evs = st.multiselect("募集種目", utils.EVENT_OPTIONS, default=utils.EVENT_OPTIONS)
        status = st.selectbox("初期ステータス", ["募集中", "準備中"])

        if st.form_submit_button("登録"):
            data = {
                "name": name, "date": date_val, "deadline": deadline, "location": loc, 
                "events": evs, "status": status, "valid_start": valid_start, "valid_end": valid_end
            }
            if db.save_competition(data):
                st.success("登録しました")

# views/admin.py

def page_result_registration():
    st.title("⏱️ 結果登録 & 連携")
    
    comps = db.load_competitions()
    comps.sort(key=lambda x: x["date"], reverse=True)
    comp_opts = {f"{c['date']} {c['name']}": c for c in comps}
    
    sel = st.selectbox("大会を選択", list(comp_opts.keys()))
    if not sel: return
    target_comp = comp_opts[sel]
    cid = str(target_comp["id"])

    t1, t2, t3 = st.tabs(["1️⃣ スタートリスト作成", "2️⃣ 結果入力(組・レーン)", "3️⃣ 報告作成"])
    
    # === Tab 1: スタートリスト作成 ===
    with t1:
        st.caption("エントリー情報からリストを作成し、組・レーン・時間を入力して保存します。ここで保存すると「タイムテーブル」に反映されます。")
        
        # 既存のスタートリストをロード
        current_sl = db.load_start_list(target_comp["id"])
        
        # まだ作成されていない場合、エントリーからひな形を作るボタン
        if not current_sl:
            st.info("まだスタートリストがありません。エントリー情報から作成しますか？")
            if st.button("エントリーから初期データを作成"):
                all_entries = db.load_entries()
                users_db = db.load_users()
                target_entries = [e for e in all_entries if str(e["comp_id"]) == str(target_comp["id"])]
                
                init_data = []
                for e in target_entries:
                    uid = str(e["user_id"])
                    u_info = users_db.get(uid, {})
                    u_pbs = u_info.get("pbs", {})
                    try: evs = json.loads(e["events"])
                    except: evs = []
                    try: times = json.loads(e["times"])
                    except: times = {}
                    
                    for ev in evs:
                        init_data.append({
                            "競技始": "", "種目": ev, "組": "", "レーン": "", 
                            "ナンバー": u_info.get("number", ""), 
                            "氏名": e["user_name"], 
                            "現PB": u_pbs.get(ev, "-"), 
                            "目標記録": times.get(ev, ""),
                            "所属": u_info.get("affiliation", ""),
                            "招集始": "", "招集終": "", "備考": ""
                        })
                # データフレーム化してセッションへ
                st.session_state["editor_sl_data"] = pd.DataFrame(init_data)
                st.rerun()
        
        # データがある場合 (DBまたはセッション)
        if "editor_sl_data" not in st.session_state:
             if current_sl:
                 st.session_state["editor_sl_data"] = pd.DataFrame(current_sl)
        
        if "editor_sl_data" in st.session_state:
            df_input = st.session_state["editor_sl_data"]
            
            # 列の並び順整理
            pref_cols = ["競技始", "種目", "組", "レーン", "ナンバー", "氏名", "現PB", "目標記録", "所属", "招集始", "招集終", "備考"]
            # 存在しない列があれば追加
            for c in pref_cols:
                if c not in df_input.columns: df_input[c] = ""
            
            # 編集エディタ
            edited_df = st.data_editor(
                df_input[pref_cols],
                num_rows="dynamic",
                use_container_width=True,
                height=500,
                key="sl_editor_widget"
            )
            
            col_btn1, col_btn2 = st.columns([1, 2])
            if col_btn1.button("スタートリストを保存", type="primary"):
                # 辞書リストに変換して保存
                save_data = edited_df.to_dict(orient="records")
                if db.save_start_list_overwrite(target_comp["id"], save_data):
                    st.success("✅ 保存しました！ これでタイムテーブル画面に表示されます。")
                    # 再読み込み用にキャッシュ更新
                    del st.session_state["editor_sl_data"]
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("保存に失敗しました")
                    
            # CSVインポート機能 (手元のCSVを使いたい場合)
            with st.expander("CSVファイルから取り込む"):
                uploaded_csv = st.file_uploader("CSVをアップロード", type=["csv"])
                if uploaded_csv:
                    try:
                        df_upload = pd.read_csv(uploaded_csv, encoding="cp932") # ExcelなどからのCSVはcp932が多い
                        st.session_state["editor_sl_data"] = df_upload
                        st.success("CSVを読み込みました。上の表を確認して「保存」を押してください。")
                        st.rerun()
                    except:
                        st.error("読み込み失敗。文字コードを確認してください。")

    # === Tab 2: 結果入力 ===
    # Tab 2: 結果入力 (ここを強化)
    with t2:
        st.markdown("#### 組・レーンごとの結果登録")
        st.caption("個人がダッシュボードから入力した結果があれば、自動でここに表示されます。")
        
        # 1. スタートリスト読み込み
        sl = db.load_start_list(cid)
        if not sl:
            st.warning("スタートリストがありません。Tab1で作成してください。")
        else:
            df = pd.DataFrame(sl)
            
            # 2. 既存リザルト読み込み (個人入力分含む)
            existing_results = db.load_results(cid)
            # マッチング用マップ: (user_id, event) -> result_data
            res_map = {}
            for r in existing_results:
                key = (str(r.get("user_id")), r.get("event"))
                res_map[key] = r
            
            # 3. データフレームに結果をマージ
            # user_nameからuser_idを逆引きする必要がある (StartListにはNameしかない場合が多いので)
            users = db.load_users()
            name_to_id = {u["name"]: u["id"] for u in users.values()}
            
            # まだdfに結果列がない場合、または空の場合、DBから埋める
            if "結果" not in df.columns: df["結果"] = ""
            if "風" not in df.columns: df["風"] = ""
            if "順位" not in df.columns: df["順位"] = ""
            
            for idx, row in df.iterrows():
                # 名前からID特定
                uid = name_to_id.get(row.get("氏名"), "")
                evt = row.get("種目")
                
                # DBにリザルトがあればセット (まだ入力されていなければ空)
                if (uid, evt) in res_map and not str(row.get("結果", "")):
                    r_data = res_map[(uid, evt)]
                    df.at[idx, "結果"] = r_data.get("result", "")
                    df.at[idx, "風"] = r_data.get("wind", "")
                    df.at[idx, "順位"] = r_data.get("rank", "")
            
            # 4. エディタ表示
            edited = st.data_editor(df, key="res_grid_editor", num_rows="dynamic")
            
            if st.button("結果を確定・保存"):
                save_list = []
                for _, row in edited.iterrows():
                    res_val = str(row.get("結果", "")).strip()
                    if not res_val: continue
                    
                    uid = name_to_id.get(row.get("氏名"), "")
                    if not uid: continue # ID特定できないと保存不可
                    
                    save_list.append({
                        "comp_id": cid,
                        "user_id": uid,
                        "event": row.get("種目"),
                        "division": row.get("区分", ""),
                        "round": row.get("ラウンド", ""),
                        "heat": row.get("組", ""),
                        "lane": row.get("レーン", ""),
                        "result": res_val,
                        "wind": row.get("風", ""),
                        "rank": row.get("順位", ""),
                        "comment": row.get("備考", "")
                    })
                
                if db.save_results_batch(save_list):
                    st.success("保存しました！")

    # === Tab 3: 報告・メーリス作成 ===
    with t3:
        st.subheader("📢 結果報告の作成")
        st.caption("入力された結果をもとに、News用とメーリス用の文章を自動生成します。")
        
        if st.button("文章を生成する", type="primary"):
            # 1. データ収集
            results = db.load_results(target_comp["id"])
            users = db.load_users()
            
            if not results:
                st.error("まだ結果が登録されていません。Tab2で入力してください。")
            else:
                # 2. 文章構築ロジック
                # 種目ごとにグループ化
                df = pd.DataFrame(results)
                
                # 並び替え: 種目 -> 組 -> レーン (または順位)
                # 数値変換してソートできるようにする
                df["heat_num"] = pd.to_numeric(df["heat"], errors='coerce').fillna(999)
                df["lane_num"] = pd.to_numeric(df["lane"], errors='coerce').fillna(999)
                
                # 種目リスト (マスタなどがあればその順、なければ出現順)
                events = sorted(df["event"].unique())
                
                # --- 本文生成 ---
                body_text = ""
                
                for ev in events:
                    body_text += f"\n{ev}\n"
                    df_ev = df[df["event"] == ev].sort_values(["heat_num", "lane_num"])
                    
                    for _, r in df_ev.iterrows():
                        # 学年 (B4など) を取得
                        uid = str(r["user_id"])
                        u = users.get(uid, {})
                        short_grade = utils.get_short_grade(u.get("grad_year", ""), u.get("univ_cat", "学部"))
                        
                        # 名前
                        name = r["user_name"]
                        
                        # 記録
                        res = r["result"]
                        
                        # 組-レーン (例: 1-7)
                        heat = r["heat"]
                        lane = r["lane"]
                        pos_str = f"{heat}-{lane}" if heat and lane else "-"
                        
                        # 備考 (PBなど)
                        comment = r["comment"]
                        
                        # 行生成: "1-7 駒野陽高(B4) 10’13″77 PB"
                        line = f"{pos_str} {name}({short_grade}) {res}"
                        if comment:
                            line += f" {comment}"
                        
                        body_text += line + "\n"

                # --- News用テキスト ---
                date_dt = datetime.strptime(target_comp['date'], '%Y-%m-%d')
                date_str = f"{date_dt.month}月{date_dt.day}日（{['月','火','水','木','金','土','日'][date_dt.weekday()]}）"
                
                news_intro = f"{date_str}に{target_comp.get('location','競技場')}にて行われた、{target_comp['name']}の結果をお知らせいたします。\n"
                news_footer = "\n結果は以上です。お疲れ様でした。"
                
                full_news_text = news_intro + body_text + news_footer
                
                # --- メーリス用テキスト ---
                me_name = st.session_state.user_info["name"]
                mail_intro = f"こんばんは\n広報の{me_name}です。\n" + news_intro
                
                full_mail_text = mail_intro + body_text + news_footer
                
                # 3. 表示 & アクション
                
                c_mail, c_news = st.columns(2)
                
                with c_mail:
                    st.info("✉️ メーリス・後援会送信用")
                    st.text_area("コピーして使ってください", full_mail_text, height=400)
                
                with c_news:
                    st.success("🌍 公式HP News掲載用")
                    st.text_area("内容確認", full_news_text, height=300)
                    
                    if st.button("この内容でNewsに掲載する"):
                        import uuid
                        news_data = {
                            "id": str(uuid.uuid4()),
                            "date": target_comp["date"],
                            "title": f"【結果報告】{target_comp['name']}",
                            "content": full_news_text
                        }
                        if db.save_news(news_data):
                            st.balloons()
                            st.success("Newsに掲載しました！トップページを確認してください。")
                        else:
                            st.error("保存エラー")

def page_entry_management():
    st.title("📋 エントリー管理・出力")
    
    comps = db.load_competitions()
    if not comps: st.warning("大会データがありません"); return

    comps.sort(key=lambda x: x['date'], reverse=True)
    comp_opts = {f"{c['date']} {c['name']}": c for c in comps}
    
    # ★IDから大会情報（名前・日付）を引くための辞書
    comp_id_map = {str(c["id"]): c for c in comps}
    
    selected_comp_key = st.selectbox("管理する大会を選択", list(comp_opts.keys()))
    target_comp = comp_opts[selected_comp_key]


    st.divider()
    c_st, c_btn = st.columns([2, 1])
    
    current_status = target_comp.get("status", "募集中")
    status_options = ["募集中", "締切", "終了", "準備中"]
    
    # 現在のステータスがリストにない場合の対策
    if current_status not in status_options:
        status_options.append(current_status)
        
    new_status = c_st.selectbox(
        "募集ステータス変更", 
        status_options, 
        index=status_options.index(current_status)
    )
    
    if c_btn.button("ステータス更新"):
        if new_status == current_status:
            st.warning("ステータスが変わっていません")
        else:
            if db.update_competition_status(target_comp["id"], new_status):
                st.success(f"ステータスを「{new_status}」に更新しました！")
                time.sleep(1)
                st.rerun()
            else:
                st.error("更新に失敗しました")


    
    # 有効期間情報の取得 (None対策済み)
    v_start = target_comp.get("valid_start", "")
    v_end = target_comp.get("valid_end", "")
    if str(v_start) == "None": v_start = ""
    if str(v_end) == "None": v_end = ""
    
    st.markdown(f"### {target_comp['name']} のエントリーリスト")
    
    # ★ entries はここでロードする (NameError回避)
    entries = db.load_entries(target_comp["id"])
    if not entries: st.info("エントリーなし"); return

    users_db = db.load_users()

    processed_rows = []
    
    with st.spinner("集計中..."):
        for e in entries:
            try: selected_events = json.loads(e["events"])
            except: selected_events = []
            try: time_dict = json.loads(e["times"])
            except: time_dict = {}
            
            user_info = users_db.get(str(e["user_id"]), {})
            user_pbs = user_info.get("pbs", {})
            
            for ev in selected_events:
                seed_time = time_dict.get(ev, "")
                
                # 1. DBベスト
                db_best_data = db.get_user_best_in_period(e["user_id"], ev, v_start, v_end)
                db_best_res = db_best_data["result"] if db_best_data else None
                
                # 2. プロフィールベスト
                profile_pb = user_pbs.get(ev, "")
                
                # 3. 比較 & 大会名・日付の安全な取得
                final_best = "-"
                final_comp = "-"
                final_date = "-" # ★達成日用の変数
                
                # --- 情報補完用の便利関数 ---
                def extract_info(data):
                    if not data: return "-", "-"
                    
                    # A. 大会名の取得
                    c_name = data.get("comp_name") # まずデータ内を探す
                    if not c_name:
                        # なければIDから探す
                        cid = str(data.get("comp_id", ""))
                        if cid in comp_id_map:
                            c_name = comp_id_map[cid]["name"]
                        else:
                            c_name = "-"
                    
                    # B. 日付の取得
                    c_date = data.get("date") # まずデータ内を探す
                    if not c_date:
                        # なければIDから探す
                        cid = str(data.get("comp_id", ""))
                        if cid in comp_id_map:
                            c_date = str(comp_id_map[cid]["date"])
                        else:
                            c_date = "-"
                            
                    return c_name, c_date
                # ---------------------------

                if v_start: 
                    # 【期間指定あり】 -> DBのみ採用
                    if db_best_res:
                        final_best = db_best_res
                        if db_best_data.get("wind"): final_best += f" ({db_best_data['wind']})"
                        
                        # 安全に取得
                        final_comp, final_date = extract_info(db_best_data)
                else:
                    # 【期間指定なし】 -> プロフィールと比較
                    better_res = utils.get_better_record(profile_pb, db_best_res, ev)
                    
                    if better_res and better_res != "-":
                        final_best = better_res
                        
                        if better_res == db_best_res and db_best_res is not None:
                            # DB採用
                            if db_best_data.get("wind"): final_best += f" ({db_best_data['wind']})"
                            final_comp, final_date = extract_info(db_best_data)
                        else:
                            # 自己申告採用
                            final_comp = "自己申告"
                            final_date = "-" # 自己申告は日付不明

                processed_rows.append({
                    "User ID": e["user_id"], 
                    "氏名": e["user_name"], 
                    "種目": ev,
                    "申請記録": seed_time,
                    "資格記録(Best)": final_best,
                    "達成大会": final_comp,
                    "達成日": final_date, # ★列追加
                    "備考": e["comment"],
                    "登録日時": e.get("timestamp", "")[:16]
                })

    df = pd.DataFrame(processed_rows)
    filter_ev = st.selectbox("種目で絞り込み", ["全て"] + sorted(list(set(df["種目"]))))
    if filter_ev != "全て": df_show = df[df["種目"] == filter_ev]
    else: df_show = df

    st.dataframe(df_show, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(label="📥 CSVダウンロード", data=csv, file_name=f"entry_list_{target_comp['name']}.csv", mime="text/csv")



# views/admin.py の page_migration をこれに書き換え

def page_migration():
    st.title("📥 データ登録・インポート")
    
    tab1, tab2, tab3 = st.tabs(["1. 個別登録 (1名)", "2. 名簿一括 (Excel)", "3. リザルト一括"])
    
    # === 共通関数 ===
    def normalize_date(d):
        if pd.isna(d) or d == "": return ""
        try: return pd.to_datetime(d).strftime("%Y-%m-%d")
        except: return str(d).replace("/", "-").split(" ")[0]

    def to_int_str(val):
        if pd.isna(val) or val == "": return ""
        try: return str(int(float(val)))
        except: return str(val).strip()

    def guess_role(title):
        if not title or title == "なし": return "player"
        t = str(title)
        if any(k in t for k in ["主将", "副主将"]): return "super"
        if "競技会" in t: return "comp"
        if "広報" in t: return "pr"
        if any(k in t for k in ["システム", "管理者", "主務"]): return "admin"
        return "player"

    # === Tab 1: 個別登録 ===
    with tab1:
        st.markdown("### 👤 1名だけ追加登録")
        st.caption("新入部員など、少数の追加はこちらが便利です。")
        current_users = db.load_users()
        existing_ids = set(current_users.keys())
        
        def generate_unique_id(ex_ids):
            while True:
                nid = f"uec{random.randint(0, 999):03d}"
                if nid not in ex_ids: 
                    ex_ids.add(nid)
                    return nid
        
        with st.form("single_register_form"):
            default_id = generate_unique_id(existing_ids)
            default_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            
            name = st.text_input("氏名 (必須)")
            c1, c2 = st.columns(2)
            uid = c1.text_input("ユーザーID", value=default_id)
            pw = c2.text_input("パスワード", value=default_pass)
            
            c3, c4 = st.columns(2)
            block = c3.selectbox("ブロック", ["短距離・跳躍・投擲", "中距離", "長距離", "マネージャー", "その他"])
            aff = c4.selectbox("所属", ["情報理工学域 I類", "情報理工学域 II類", "情報理工学域 III類", "大学院", "その他"])
            
            if st.form_submit_button("この内容で登録"):
                if not name:
                    st.error("氏名は必須です。")
                elif uid in existing_ids:
                    st.error(f"エラー: ID '{uid}' は既に使用されています。別のIDにしてください。")
                else:
                    new_user = {
                        "user_id": uid,
                        "name": name.strip().replace("　", " "),
                        "password": pw, "block": block, "affiliation": aff,
                        "role": "player", "status": "現役"
                    }
                    if db.save_user(uid, new_user):
                        st.success(f"✅ {name} さんを登録しました！ (ID: {uid})")
                        current_users[uid] = new_user 
                    else: st.error("保存に失敗しました。")

    # === Tab 2: 名簿一括 ===
    with tab2:
        st.markdown("### 📂 名簿データの一括登録・更新")
        st.info("すべての項目（カナ、役職、種目など）を取り込めます。")
        
        uploaded_file = st.file_uploader("名簿ファイル", type=["csv", "xlsx"], key="uploader_users")
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    try: df = pd.read_csv(uploaded_file, encoding="cp932") 
                    except: uploaded_file.seek(0); df = pd.read_csv(uploaded_file, encoding="utf-8")
                else:
                    df = pd.read_excel(uploaded_file)
            except Exception as e:
                st.error(f"ファイル読み込みエラー: {e}")
                df = None
            
            if df is not None:
                st.dataframe(df.head(3))
                cols = df.columns.tolist()
                
                def find_idx(keywords, columns):
                    for k in keywords:
                        for i, col in enumerate(columns):
                            if k in str(col): return i
                    return 0

                st.markdown("##### 列の対応付け")
                c1, c2, c3, c4 = st.columns(4)
                col_name = c1.selectbox("氏名 (必須)", cols, index=find_idx(["氏名", "名前"], cols))
                col_kana = c2.selectbox("カナ", ["なし"] + cols, index=find_idx(["カナ", "フリガナ", "ヨミ"], cols) + (1 if find_idx(["カナ", "フリガナ", "ヨミ"], cols) else 0))
                col_id = c3.selectbox("ID (指定する場合)", ["(自動生成)"] + cols, index=0)
                col_pw = c4.selectbox("パスワード (指定する場合)", ["(自動生成)"] + cols, index=0)

                c5, c6, c7, c8 = st.columns(4)
                col_aff = c5.selectbox("所属", ["なし"] + cols, index=find_idx(["所属", "学科", "類"], cols) + (1 if find_idx(["所属"], cols) else 0))
                col_cat = c6.selectbox("課程 (学部/修士)", ["なし"] + cols, index=find_idx(["課程"], cols) + (1 if find_idx(["課程"], cols) else 0))
                col_year = c7.selectbox("卒業予定年 (数値)", ["なし"] + cols, index=find_idx(["卒業", "卒年", "年度"], cols) + (1 if find_idx(["卒業"], cols) else 0))
                col_block = c8.selectbox("ブロック", ["なし"] + cols, index=find_idx(["ブロック"], cols) + (1 if find_idx(["ブロック"], cols) else 0))

                c9, c10, c11 = st.columns(3)
                col_role = c9.selectbox("役職", ["なし"] + cols, index=find_idx(["役職"], cols) + (1 if find_idx(["役職"], cols) else 0))
                col_status = c10.selectbox("ステータス", ["なし"] + cols, index=find_idx(["ステータス", "状態"], cols) + (1 if find_idx(["ステータス"], cols) else 0))
                col_events = c11.selectbox("専門種目 (カンマ区切り)", ["なし"] + cols, index=find_idx(["種目", "専門"], cols) + (1 if find_idx(["種目"], cols) else 0))

                st.divider()
                overwrite = st.checkbox("⚠️ 同名のユーザーが既にいる場合、情報を上書きする", value=False)
                
                if st.button("名簿を取り込む", type="primary"):
                    current_users_dict = db.load_users()
                    name_map = {}
                    for uid, u in current_users_dict.items():
                        clean = str(u.get("name", "")).strip().replace("　", " ")
                        name_map[clean] = uid
                    existing_ids = set(current_users_dict.keys())
                    
                    added_count = 0; updated_count = 0; skipped_count = 0
                    
                    def get_rnd_id(ex_ids):
                        while True:
                            nid = f"uec{random.randint(0, 999):03d}"
                            if nid not in ex_ids: 
                                ex_ids.add(nid)
                                return nid
                                
                    users_to_save = []
                    
                    # 既存データをリスト化（更新対象以外はそのまま残す）
                    for uid, u in current_users_dict.items():
                         # load_usersのデータ構造を維持しつつリストへ
                         # ここでは全データ上書き関数を使うため、辞書リストを作る
                         users_to_save.append(u)

                    # 辞書のリストだと更新が面倒なので、uidをキーにした辞書で管理して最後にリスト化する
                    save_map = {u["user_id"]: u for u in users_to_save}

                    for _, row in df.iterrows():
                        raw_name = str(row[col_name])
                        if pd.isna(raw_name) or raw_name == "" or str(raw_name) == "nan": continue
                        clean_name = str(raw_name).strip().replace("　", " ")
                        
                        u_kana = str(row[col_kana]) if col_kana != "なし" and pd.notna(row[col_kana]) else ""
                        u_aff = str(row[col_aff]) if col_aff != "なし" and pd.notna(row[col_aff]) else ""
                        u_cat = str(row[col_cat]) if col_cat != "なし" and pd.notna(row[col_cat]) else "学部"
                        u_block = str(row[col_block]) if col_block != "なし" and pd.notna(row[col_block]) else ""
                        u_role_title = str(row[col_role]) if col_role != "なし" and pd.notna(row[col_role]) else ""
                        u_status = str(row[col_status]) if col_status != "なし" and pd.notna(row[col_status]) else "現役"
                        
                        u_grad = ""
                        if col_year != "なし" and pd.notna(row[col_year]):
                            try: u_grad = int(float(str(row[col_year])))
                            except: pass
                        
                        u_events = []
                        if col_events != "なし" and pd.notna(row[col_events]):
                            raw_evs = str(row[col_events])
                            u_events = [e.strip() for e in raw_evs.replace("、", ",").split(",") if e.strip()]

                        target_uid = None
                        is_new = False
                        
                        if clean_name in name_map:
                            if overwrite:
                                target_uid = name_map[clean_name]
                                updated_count += 1
                            else:
                                skipped_count += 1
                                continue
                        else:
                            if col_id != "(自動生成)" and pd.notna(row[col_id]):
                                target_uid = str(row[col_id]).strip()
                                existing_ids.add(target_uid)
                            else:
                                target_uid = get_rnd_id(existing_ids)
                            is_new = True
                            added_count += 1
                            
                            if col_pw != "(自動生成)" and pd.notna(row[col_pw]):
                                pw = str(row[col_pw]).strip()
                            else:
                                pw = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                            
                            # 新規作成初期値
                            save_map[target_uid] = {
                                "user_id": target_uid, "password": pw, "role": "player", "name": clean_name
                            }

                        # データを適用
                        user_obj = save_map[target_uid]
                        user_obj["name"] = clean_name
                        user_obj["user_id"] = target_uid
                        if u_kana: user_obj["name_kana"] = u_kana
                        if u_aff: user_obj["affiliation"] = u_aff
                        if u_cat: user_obj["univ_cat"] = u_cat
                        if u_grad: user_obj["grad_year"] = u_grad
                        if u_block: user_obj["block"] = u_block
                        if u_role_title: 
                            user_obj["role_title"] = u_role_title
                            user_obj["role"] = guess_role(u_role_title)
                        else:
                            if "role" not in user_obj: user_obj["role"] = "player"
                        if u_status: user_obj["status"] = u_status
                        if u_events: user_obj["events"] = u_events
                    
                    # 保存実行
                    final_list = list(save_map.values())
                    if db.save_all_users_overwrite(final_list):
                        st.success(f"保存完了！ (新規: {added_count}, 更新: {updated_count}, スキップ: {skipped_count})")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("保存処理に失敗しました。")

    # === Tab 3: リザルト一括 ===
    with tab3:
        st.markdown("### 📊 リザルトデータの一括登録")
        st.info("過去の大会結果をまとめて取り込みます。")
        uploaded_files = st.file_uploader("リザルトファイル", type=["csv", "xlsx"], accept_multiple_files=True, key="uploader_res")
        
        if uploaded_files:
            all_results = []
            users_db = db.load_users()
            name_to_id = {}
            for uid, u in users_db.items():
                clean = str(u.get("name", "")).strip().replace("　", " ")
                name_to_id[clean] = uid
            
            for file in uploaded_files:
                try:
                    if file.name.endswith('.csv'):
                        try: df = pd.read_csv(file, encoding="cp932")
                        except: file.seek(0); df = pd.read_csv(file, encoding="utf-8")
                    else:
                        df = pd.read_excel(file)
                except Exception as e:
                    st.error(f"{file.name}: 読み込みエラー {e}")
                    continue
                
                cols = df.columns.tolist()
                st.write(f"▼ {file.name} の列設定")
                
                def find_idx(keywords, columns):
                    for k in keywords:
                        for i, col in enumerate(columns):
                            if k in str(col): return i
                    return 0

                # ★修正: 列選択に「場所」を追加し、6列レイアウトに変更
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                c_name = c1.selectbox(f"氏名", cols, index=find_idx(["氏名", "名前"], cols), key=f"n_{file.name}")
                c_event = c2.selectbox(f"種目", cols, index=find_idx(["種目", "イベント"], cols), key=f"e_{file.name}")
                c_result = c3.selectbox(f"記録", cols, index=find_idx(["記録", "結果"], cols), key=f"r_{file.name}")
                c_comp = c4.selectbox(f"大会", cols, index=find_idx(["大会"], cols), key=f"c_{file.name}")
                c_date = c5.selectbox(f"月日", cols, index=find_idx(["日", "date"], cols), key=f"d_{file.name}")
                # ★追加: 場所
                c_loc = c6.selectbox(f"場所", ["なし"]+cols, index=find_idx(["場所", "会場", "location"], cols)+1 if find_idx(["場所", "会場"], cols)!=0 else 0, key=f"loc_{file.name}")
                
                d1, d2, d3, d4, d5, d6, d7 = st.columns(7)
                c_rank = d1.selectbox(f"順位", ["なし"]+cols, index=find_idx(["順位", "着順"], cols)+1 if find_idx(["順位"], cols) !=0 else 0, key=f"rk_{file.name}")
                c_wind = d2.selectbox(f"風", ["なし"]+cols, index=find_idx(["風"], cols)+1 if find_idx(["風"], cols) !=0 else 0, key=f"w_{file.name}")
                c_div = d3.selectbox(f"区分", ["なし"]+cols, index=find_idx(["区分"], cols)+1 if find_idx(["区分"], cols) !=0 else 0, key=f"div_{file.name}")
                c_round = d4.selectbox(f"ラウンド", ["なし"]+cols, index=find_idx(["ラウンド"], cols)+1 if find_idx(["ラウンド"], cols) !=0 else 0, key=f"rd_{file.name}")
                c_heat = d5.selectbox(f"組", ["なし"]+cols, index=find_idx(["組"], cols)+1 if find_idx(["組"], cols) !=0 else 0, key=f"h_{file.name}")
                c_lane = d6.selectbox(f"レーン", ["なし"]+cols, index=find_idx(["レーン"], cols)+1 if find_idx(["レーン"], cols) !=0 else 0, key=f"l_{file.name}")
                c_comment = d7.selectbox(f"備考", ["なし"]+cols, index=find_idx(["備考"], cols)+1 if find_idx(["備考"], cols) !=0 else 0, key=f"cm_{file.name}")
                st.divider()

                for _, row in df.iterrows():
                    p_name = str(row[c_name]).strip().replace("　", " ")
                    if p_name not in name_to_id: continue
                    
                    raw_res = str(row[c_result]).strip()
                    val_wind = str(row[c_wind]).strip() if c_wind != "なし" and pd.notna(row[c_wind]) else ""
                    
                    if not val_wind or val_wind == "nan":
                        val_wind = ""
                        match = re.search(r'[\(（](.*?)[\)）]', raw_res)
                        if match:
                            val_wind = match.group(1)
                            raw_res = raw_res.replace(match.group(0), "")

                    clean_res = raw_res.replace('"', '.').replace('”', '.').replace("'", ":").strip()
                    val_date = normalize_date(row[c_date])

                    # ★追加: 場所の取得
                    val_loc = str(row[c_loc]).strip() if c_loc != "なし" and pd.notna(row[c_loc]) else "場所不明"

                    all_results.append({
                        "comp_name": str(row[c_comp]), 
                        "date": val_date,
                        "location": val_loc, # ★ここに追加
                        "event": str(row[c_event]), "user_id": name_to_id[p_name], "user_name": p_name, 
                        "result": clean_res, "wind": val_wind, 
                        "rank": to_int_str(row[c_rank]) if c_rank != "なし" else "",
                        "division": str(row[c_div]).strip() if c_div != "なし" and pd.notna(row[c_div]) else "",
                        "round": str(row[c_round]).strip() if c_round != "なし" and pd.notna(row[c_round]) else "", 
                        "heat": to_int_str(row[c_heat]) if c_heat != "なし" else "", 
                        "lane": to_int_str(row[c_lane]) if c_lane != "なし" else "", 
                        "comment": str(row[c_comment]).strip() if c_comment != "なし" and pd.notna(row[c_comment]) else ""
                    })

            st.write(f"読込成功: {len(all_results)} 件")
            if st.button("一括保存", key="btn_save_res"):
                if not all_results: return
                new_results = []
                comp_map = {}
                existing_comps = db.load_competitions()
                # 既存大会を (date, name) でマッピング
                for c in existing_comps: comp_map[(c["date"], c["name"])] = c["id"]
                
                for r in all_results:
                    k = (r["date"], r["comp_name"])
                    if k in comp_map: 
                        cid = comp_map[k]
                    else:
                        # ★修正: 新規大会作成時に location と status="終了" を設定
                        import uuid
                        cid = str(uuid.uuid4())[:8]
                        db.save_competition({
                            "name": r["comp_name"], 
                            "date": r["date"], 
                            "location": r["location"], # 読み取った場所
                            "deadline": "-", 
                            "status": "終了", # ステータスを終了に
                            "events": []
                        })
                        comp_map[k] = cid
                    
                    new_results.append({
                        "comp_id": cid, "event": r["event"], "user_id": r["user_id"], "user_name": r["user_name"], 
                        "result": r["result"], "wind": r["wind"], "rank": r["rank"], 
                        "division": r["division"], "round": r["round"], "heat": r["heat"], "lane": r["lane"], "comment": r["comment"],
                        "date": r["date"]
                    })
                
                if db.save_results_batch(new_results): st.success("保存完了")
                else: st.error("エラー")


# --- views/admin.py の末尾に追加 ---

def page_accounting_admin():
    st.title("💰 会計・部費管理 (管理者)")
    
    tab1, tab2 = st.tabs(["1. 集金イベント作成", "2. 納入状況の管理"])
    
    # === Tab 1: 新規作成 ===
    with tab1:
        st.subheader("新しい集金を作成")
        with st.form("create_fee_form"):
            title = st.text_input("タイトル (例: 4月度部費, 春合宿費)")
            amount = st.number_input("金額 (円)", min_value=0, step=100, value=1000)
            deadline = st.date_input("支払期限")
            
            # 対象者の選択
            users = db.load_users()
            target_opts = ["全員 (現役)", "全員 (現役+OB)", "選択した人のみ"]
            target_type = st.radio("集金対象", target_opts)
            
            selected_uids = []
            if target_type == "選択した人のみ":
                # 名前で選択
                user_map = {f"{u['name']} ({u.get('affiliation','')})": uid for uid, u in users.items()}
                sel_names = st.multiselect("対象者を選択", list(user_map.keys()))
                selected_uids = [user_map[n] for n in sel_names]
            
            if st.form_submit_button("作成する"):
                if not title:
                    st.error("タイトルを入力してください")
                else:
                    # 対象IDリストを作成
                    final_targets = []
                    if target_type == "全員 (現役)":
                        final_targets = [uid for uid, u in users.items() if u.get("status") == "現役"]
                    elif target_type == "全員 (現役+OB)":
                        final_targets = list(users.keys())
                    else:
                        final_targets = selected_uids
                    
                    if not final_targets:
                        st.error("対象者がいません")
                    else:
                        # ステータスマップ作成 {uid: "未納"}
                        status_map = {uid: "未納" for uid in final_targets}
                        
                        import uuid
                        new_fee = {
                            "id": str(uuid.uuid4())[:8],
                            "title": title,
                            "amount": amount,
                            "deadline": str(deadline),
                            "status_map": status_map
                        }
                        
                        if db.save_fee_event(new_fee):
                            st.success(f"「{title}」を作成しました！ (対象: {len(final_targets)}名)")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("保存失敗")

    # === Tab 2: 管理・チェック ===
    with tab2:
        fees = db.load_fees()
        if not fees:
            st.info("集金イベントがありません")
        else:
            # イベント選択
            fee_opts = {f"{f['deadline']} : {f['title']}": f for f in fees}
            sel_fee_key = st.selectbox("管理する集金を選択", list(fee_opts.keys()))
            target_fee = fee_opts[sel_fee_key]
            
            st.markdown(f"### {target_fee['title']}")
            st.write(f"金額: **¥{target_fee['amount']:,}** / 期限: {target_fee['deadline']}")
            
            # ステータスマップ {uid: "未納" or "済"}
            status_map = target_fee.get("status_map", {})
            users = db.load_users()
            
            # 集計
            paid_count = list(status_map.values()).count("済")
            total_count = len(status_map)
            progress = paid_count / total_count if total_count > 0 else 0
            
            st.progress(progress)
            st.caption(f"納入済み: {paid_count} / {total_count} 名 ({int(progress*100)}%)")
            
            st.divider()
            
            # テーブルで表示・編集
            # データフレーム化して扱いやすくする
            rows = []
            for uid, status in status_map.items():
                u = users.get(str(uid), {})
                rows.append({
                    "uid": uid,
                    "氏名": u.get("name", "不明"),
                    "ステータス": status == "済", # チェックボックス用 (True/False)
                    "支払状況": status
                })
            
            if not rows:
                st.warning("対象者がいません")
            else:
                df = pd.DataFrame(rows)
                
                # 編集用データエディタ
                edited_df = st.data_editor(
                    df[["ステータス", "氏名", "支払状況"]],
                    column_config={
                        "ステータス": st.column_config.CheckboxColumn("支払済", help="チェックすると「済」になります", default=False)
                    },
                    use_container_width=True,
                    height=400,
                    key=f"editor_fee_{target_fee['id']}"
                )
                
                if st.button("変更を保存する", type="primary"):
                    # 編集結果を元のJSON形式に戻す
                    new_map = status_map.copy()
                    
                    # 名前からUIDを逆引きするのは危険なので、行の順序が変わっていない前提、
                    # あるいは df のインデックスを使って突合する
                    # ここではUIDを隠し持てないので、元のrowsの順番通りであると仮定するか、
                    # data_editorの戻り値には元のindexが維持されるのを利用
                    
                    # 一番確実なのは、edited_df の index を見て rows[index] の uid を取ること
                    for idx, row in edited_df.iterrows():
                        uid = rows[idx]["uid"]
                        is_paid = row["ステータス"]
                        new_map[uid] = "済" if is_paid else "未納"
                    
                    # 保存処理
                    target_fee["status_map"] = new_map
                    if db.save_fee_event(target_fee):
                        st.success("更新しました！")
                        time.sleep(1)
                        st.rerun()