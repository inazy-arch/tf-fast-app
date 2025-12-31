import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
import db
import utils

# ==========================================
# 1. ダッシュボード (トップ画面)
# ==========================================
def page_top():
    st.title("My Dashboard")
    user = st.session_state.user_info
    
    # ★ここで日付文字列を定義します
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    st.markdown(f"##### 👋 お疲れ様です、{user['name']} さん")

    # --- 1. 未報告の大会・種目を探す ---
    st.subheader("📝 結果の報告")
    st.caption("出場した大会が終わったら、ここからすぐに記録を入力してください。")
    
    entries = db.load_entries()
    # 自分のエントリーのみ抽出
    my_entries = [e for e in entries if str(e["user_id"]) == str(user["id"])]
    
    # 既に登録済みのリザルトを取得
    my_results = db.load_results(None)
    # (comp_id, event) のペア済みセットを作成
    done_keys = set()
    for r in my_results:
        if str(r.get("user_id")) == str(user["id"]):
            done_keys.add((str(r["comp_id"]), r["event"]))
    
    # 報告すべきリストを作成
    todo_list = []
    comps = db.load_competitions()
    comp_map = {str(c["id"]): c for c in comps}
    
    for e in my_entries:
        cid = str(e["comp_id"])
        comp = comp_map.get(cid)
        if not comp: continue
        
        # 未来の大会はまだ報告できない (今日より後の日付は除外)
        if comp["date"] > today_str: continue
        
        try: evs = json.loads(e["events"])
        except: evs = []
        
        for ev in evs:
            # まだ報告していない種目だけ追加
            if (cid, ev) not in done_keys:
                todo_list.append({
                    "comp_id": cid,
                    "comp_name": comp["name"],
                    "date": comp["date"],
                    "event": ev
                })
    
    if not todo_list:
        st.success("🎉 未報告の結果はありません。全て完了しています！")
    else:
        st.info("以下の種目の結果を入力してください。")
        
        # フォームで一括入力
        with st.form("batch_result_input"):
            results_to_submit = []
            
            for i, todo in enumerate(todo_list):
                st.markdown(f"**{todo['comp_name']}** - {todo['event']}")
                c1, c2, c3, c4 = st.columns(4)
                
                # keyを一意にする
                k_base = f"{todo['comp_id']}_{todo['event']}"
                res = c1.text_input("記録", key=f"r_{k_base}", placeholder="例: 10.50")
                wind = c2.text_input("風", key=f"w_{k_base}", placeholder="+1.5")
                rank = c3.text_input("順位", key=f"rk_{k_base}")
                comment = c4.text_input("備考", key=f"cm_{k_base}")
                
                st.divider()
                
                if res: # 記録が入力されたものだけ送信対象
                    results_to_submit.append({
                        "comp_id": todo["comp_id"],
                        "user_id": user["id"],
                        "event": todo["event"],
                        "result": res,
                        "wind": wind,
                        "rank": rank,
                        "comment": comment
                    })
            
            if st.form_submit_button("入力した結果を登録"):
                if results_to_submit:
                    if db.save_results_batch(results_to_submit):
                        st.balloons()
                        st.success("結果を登録しました！")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("記録を入力してください")

    # --- 2. エントリー申請 ---
    st.markdown("---")
    st.subheader("🚩 エントリー申請")
    
    # 募集中の大会を探す
    open_comps = [c for c in comps if c.get("status") == "募集中" and c["date"] >= today_str]
    
    if not open_comps:
        st.info("現在、募集中の大会はありません。")
    else:
        # 簡易表示 (詳細は「エントリー募集一覧」へ誘導)
        for c in open_comps:
            with st.container(border=True):
                st.write(f"**{c['name']}** (📅 {c['date']})")
                st.caption(f"締切: {c['deadline']}")
                if st.button("詳細・エントリーへ", key=f"go_entry_{c['id']}"):
                    st.session_state["menu_selection"] = "エントリー募集一覧"
                    st.rerun()


# ==========================================
# 2. アカウント情報編集
# ==========================================
def page_account():
    st.title("アカウント情報編集")
    user = st.session_state.user_info
    
    st.subheader("基本情報")
    c1, c2 = st.columns(2)
    name = c1.text_input("氏名", value=user.get("name", ""))
    kana = c2.text_input("カナ", value=user.get("name_kana", ""))
    
    c3, c4 = st.columns(2)
    
    # 課程と所属の連動
    current_cat = user.get("univ_cat", "学部")
    cat_opts = ["学部", "修士", "博士"]
    cat_idx = cat_opts.index(current_cat) if current_cat in cat_opts else 0
    univ_cat = c3.selectbox("課程", cat_opts, index=cat_idx, key="sel_cat")
    
    if univ_cat == "学部": aff_opts = utils.AFFILIATIONS_UG 
    else: aff_opts = utils.AFFILIATIONS_GRAD
        
    cur_aff = user.get("affiliation", "")
    aff_idx = aff_opts.index(cur_aff) if cur_aff in aff_opts else 0
    aff = c3.selectbox("所属", aff_opts, index=aff_idx, key="sel_aff")
    
    # 卒業年度
    raw_year = user.get("grad_year", "")
    try: default_year = int(raw_year)
    except: default_year = 2026
    grad_year = c4.number_input("卒業予定年", value=default_year, step=1)
    c4.caption(f"自動計算: {utils.calculate_grade(grad_year, univ_cat)}")
    
    st.subheader("競技情報")
    
    # ブロック
    cur_block = user.get("block", "")
    block_idx = utils.BLOCKS_LIST.index(cur_block) if cur_block in utils.BLOCKS_LIST else 0
    block = st.selectbox("ブロック", utils.BLOCKS_LIST, index=block_idx)
    
    # 専門種目
    my_events = st.multiselect("専門種目", utils.EVENT_OPTIONS, default=user.get("events", []))
    
    pbs = {}
    if my_events:
        st.markdown("##### 🏁 入部前ベスト (高校PBなど)")
        st.caption("※ 大学での記録は自動計算されます。ここには電通大陸部入部前のベストなどを入力してください。")
        cols = st.columns(2)
        old_pbs = user.get("pbs", {})
        for i, ev in enumerate(my_events):
            val = old_pbs.get(ev, "")
            pbs[ev] = cols[i%2].text_input(f"{ev}", value=val, key=f"pb_input_{ev}")

    # その他
    c_role1, c_role2 = st.columns(2)
    cur_role = user.get("role_title", "なし")
    role_idx = utils.ROLES_LIST.index(cur_role) if cur_role in utils.ROLES_LIST else 0
    role = c_role1.selectbox("役職", utils.ROLES_LIST, index=role_idx)
    
    current_status = user.get("status", "現役")
    status_opts = ["現役", "OB", "OG", "休部"]
    if current_status not in status_opts: status_opts.append(current_status)
    my_status = c_role2.selectbox("ステータス", status_opts, index=status_opts.index(current_status))

    if st.button("基本情報を保存", type="primary"):
        update_data = user.copy()
        update_data.update({
            "name": name, "name_kana": kana, "univ_cat": univ_cat, "affiliation": aff, 
            "grad_year": grad_year, "block": block, "events": my_events, 
            "pbs": pbs, "role_title": role, "status": my_status
        })
        if db.save_user(user["id"], update_data):
            st.session_state.user_info = update_data
            st.success("基本情報を保存しました")
            time.sleep(1)
            st.rerun()

    st.divider()

    # プロフィール画像・ひとこと
    st.subheader("👤 プロフィール編集")
    with st.form("profile_edit_form"):
        current_bio = user.get("bio", "")
        new_bio = st.text_area("ひとこと (50文字以内)", value=current_bio, max_chars=100)
        
        st.write("プロフィール画像")
        if user.get("image"):
            st.image(user["image"], width=100, caption="現在")
        uploaded_file = st.file_uploader("画像をアップロード", type=["jpg", "png", "jpeg"])
        
        if st.form_submit_button("プロフィールを更新"):
            updates = {"bio": new_bio}
            if uploaded_file:
                img_data = utils.process_image_to_base64(uploaded_file)
                if img_data: updates["image"] = img_data
            
            user.update(updates)
            if db.save_user(user["user_id"], user):
                st.session_state.user_info = user
                st.success("更新しました！")
                time.sleep(1)
                st.rerun()


# ==========================================
# 3. エントリー募集一覧 & モーダル
# ==========================================
@st.dialog("エントリー登録・編集")
def entry_modal(user, comp, default_data=None):
    st.subheader(f"大会: {comp['name']}")
    st.caption(f"開催日: {comp['date']} / 場所: {comp['location']}")
    
    try: allowed_events = json.loads(comp["events"])
    except: allowed_events = []
    
    default_evs = []
    default_times = {}
    default_comment = ""
    
    if default_data:
        try: default_evs = json.loads(default_data["events"])
        except: pass
        try: default_times = json.loads(default_data["times"])
        except: pass
        default_comment = default_data.get("comment", "")
    
    selected_evs = st.multiselect("出場種目を選択", allowed_events, default=default_evs)
    
    times_input = {}
    if selected_evs:
        st.markdown("---")
        st.write("⏱️ 申請タイム")
        for ev in selected_evs:
            val = default_times.get(ev, "")
            times_input[ev] = st.text_input(f"{ev} の申請タイム", value=val, placeholder="例: 11.50")
            
    st.markdown("---")
    comment = st.text_area("備考", value=default_comment, placeholder="リレー希望など")
    
    btn_label = "情報を更新する" if default_data else "エントリーする"
    
    if st.button(btn_label, type="primary"):
        if not selected_evs:
            st.error("種目を1つ以上選択してください")
        else:
            entry_data = {
                "comp_id": comp["id"],
                "user_id": user["id"],
                "user_name": user["name"],
                "events": selected_evs,
                "times": times_input,
                "comment": comment
            }
            if db.save_entry(entry_data):
                st.success("完了しました！")
                time.sleep(1)
                st.rerun()

def page_entry_recruitment():
    st.title("📣 エントリー募集中の大会")
    user = st.session_state.user_info
    comps = db.load_competitions()
    active_comps = [c for c in comps if c.get("status") in ["募集中", "締切"]]
    
    if not active_comps:
        st.info("現在募集中の大会はありません")
        return

    active_comps.sort(key=lambda x: x['date'])
    all_entries = db.load_entries()
    my_entries_map = {str(e["comp_id"]): e for e in all_entries if str(e["user_id"]) == str(user["id"])}

    for comp in active_comps:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            status = comp.get("status", "募集中")
            color = "red" if status == "締切" else "green"
            
            c1.markdown(f"### {comp['name']} <span style='color:{color}; font-size:0.8em; border:1px solid {color}; border-radius:4px; padding:2px;'>{status}</span>", unsafe_allow_html=True)
            c1.write(f"📅 **{comp['date']}**　📍 {comp['location']}")
            c1.write(f"⚠️ 締切: {comp['deadline']}")
            
            my_entry = my_entries_map.get(str(comp["id"]))
            
            with c2:
                st.write("") 
                if status == "締切":
                    if my_entry: st.success("✅ 済"); st.caption("変更不可")
                    else: st.error("受付終了")
                else:
                    if my_entry:
                        st.success("✅ 済")
                        if st.button("変更", key=f"edit_{comp['id']}"):
                            entry_modal(user, comp, default_data=my_entry)
                    else:
                        if st.button("登録", key=f"new_{comp['id']}"):
                            entry_modal(user, comp, default_data=None)
            
            if my_entry:
                try: evs = json.loads(my_entry["events"])
                except: evs = []
                st.caption(f"登録種目: {', '.join(evs)}")


# ==========================================
# 4. タイムテーブル
# ==========================================
def page_time_table():
    st.title("📅 タイムテーブル・スタートリスト")
    
    comps = db.load_competitions()
    # ★ここでもtoday_strが必要
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 未来または本日の大会
    future_comps = [c for c in comps if c["date"] >= today_str or c.get("status") != "終了"]
    future_comps.sort(key=lambda x: x["date"])
    
    if not future_comps:
        st.info("現在、予定されている大会はありません。")
        return

    comp_opts = {f"{c['date']} {c['name']}": c for c in future_comps}
    selected_key = st.selectbox("大会を選択", list(comp_opts.keys()))
    target_comp = comp_opts[selected_key]
    
    st.markdown(f"### 📍 {target_comp['name']}")
    
    start_list = db.load_start_list(target_comp["id"])
    if not start_list:
        st.info("まだスタートリスト(番組編成)は公開されていません。")
        return
        
    df = pd.DataFrame(start_list)
    df = df.fillna("")
    if "競技始" in df.columns:
        df = df.sort_values(by=["競技始", "種目", "組", "レーン"])
    
    user = st.session_state.user_info
    my_rows = df[df["氏名"] == user["name"]]
    
    if not my_rows.empty:
        st.success("✅ **あなたの出場予定**")
        disp_cols = [c for c in ["競技始", "種目", "組", "レーン", "招集始"] if c in df.columns]
        st.dataframe(my_rows[disp_cols], hide_index=True)
        st.divider()
    
    st.subheader("📋 全体リスト")
    all_events = df["種目"].unique()
    filter_ev = st.multiselect("種目で絞り込み", all_events)
    
    if filter_ev: df_show = df[df["種目"].isin(filter_ev)]
    else: df_show = df
        
    show_cols = ["競技始", "種目", "組", "レーン", "ナンバー", "氏名", "現PB", "目標記録", "所属", "招集始", "招集終"]
    final_cols = [c for c in show_cols if c in df_show.columns]
    
    st.dataframe(df_show[final_cols], hide_index=True, use_container_width=True, height=600)


# ==========================================
# 5. 部員名簿 (簡易版)
# ==========================================
def page_member_list():
    st.title("部員名簿")
    users = db.load_users()
    disp = []
    for uid, u in users.items():
        disp.append({
            "氏名": u["name"],
            "役職": u.get("role_title", "-"),
            "ブロック": u.get("block", "-"),
            "専門": ", ".join(u.get("events", []))
        })
    st.dataframe(disp, use_container_width=True)


# ==========================================
# 6. 会計
# ==========================================
def page_accounting_member():
    st.title("💸 部費・集金状況")
    user = st.session_state.user_info
    my_uid = str(user["user_id"])
    fees = db.load_fees()
    
    my_fees = []
    for f in fees:
        s_map = f.get("status_map", {})
        if my_uid in s_map:
            my_fees.append({
                "title": f["title"],
                "amount": f["amount"],
                "deadline": f["deadline"],
                "status": s_map[my_uid]
            })
    
    if not my_fees:
        st.info("現在、あなたへの請求はありません。")
        return
        
    unpaid_total = sum([f["amount"] for f in my_fees if f["status"] == "未納"])
    
    if unpaid_total > 0: st.error(f"🚨 未払いの合計: ¥{unpaid_total:,}")
    else: st.success("✅ 全て支払い済みです！")
        
    st.divider()
    for f in my_fees:
        is_paid = (f["status"] == "済")
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"#### {f['title']}")
            c1.caption(f"期限: {f['deadline']}")
            c2.markdown(f"**¥{f['amount']:,}**")
            
            if is_paid: c2.success("支払済")
            else: c2.error("未払い"); c1.warning("会計係へお支払いください")


# ==========================================
# 7. ブログ投稿
# ==========================================
def page_blog_write():
    st.title("📝 ブログを書く")
    
    with st.form("blog_write_form"):
        title = st.text_input("タイトル")
        content = st.text_area("本文", height=300)
        uploaded = st.file_uploader("画像 (任意)", type=["jpg", "png"])
        
        if st.form_submit_button("投稿する"):
            if not title or not content:
                st.error("タイトルと本文は必須です")
                return
            
            import uuid
            img_data = ""
            if uploaded:
                img_data = utils.process_image_to_base64(uploaded)
            
            user = st.session_state.user_info
            
            blog_data = {
                "id": str(uuid.uuid4()),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "title": title,
                "content": content,
                "author_name": user["name"],
                "author_id": user["user_id"],
                "image": img_data
            }
            
            if db.save_blog(blog_data):
                st.success("投稿しました！")
                time.sleep(1)
                st.rerun()
            else:
                st.error("投稿エラー")