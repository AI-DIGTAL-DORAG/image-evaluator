import streamlit as st
from PIL import Image
import pandas as pd
import tempfile
import os
from zipfile import ZipFile

st.set_page_config(layout="wide")
st.title("AI画像評価システム｜Noリネーム＋スコア名ZIP完全版")

# --- 評価指示プロンプト（CSV1行目に内蔵） ---
eval_instruction = """【AI画像・映像審査テンプレ（必ず守ること）】
あなたはAI画像/SNS映像作品の審査員です。
以下4項目（各100点満点）で“必ず画像1枚ずつ独立して”絶対評価してください。他の画像との比較や順位付けは一切せず、それぞれの作品が持つ魅力や完成度だけを基準に評価します。
1. 総合スコア（TotalScore／100点満点）: 静止画、映像化、技術、唯一性、世界観、物語性など全要素を総合的に採点
2. BuzzScore（バズ期待値／100点満点）: SNS・タイムライン・サムネイルでの一発バズ力・拡散力のみを評価
3. StillScore（静止画スコア／100点満点）: 一枚絵としての美しさ・構図・色彩・芸術性・唯一性など静止画完成度を評価
4. VideoScore（映像適性スコア／100点満点）: SORAやMV化した際にどれだけ映えるか・動かしやすいか・映像向きかを評価
Reason: 各項目ごと、なぜその得点になったかを必ずコメント
【必須運用ルール】
- 1枚ごとに完全独立で評価。比較/順位づけ/意図的な差配点は厳禁
- 各項目の意味・観点を明確に分け、重複評価・曖昧採点は不可
- 採点は「No,TotalScore,BuzzScore,StillScore,VideoScore,Reason」のCSV形式で
- Reason欄には点差の理由・各軸の強弱も必ず記述
【出力指示】
- 上記観点を厳守し、評価結果をCSV形式で出力
- 評価CSVをダウンロード後、「評価済みCSVアップロード（4軸スコア＋コメント付きファイル名ZIP化・高画質サムネ/拡大）」システムにそのまま投入
- 必要なファイル名自動生成・ZIP一括管理も連携OK
【例】
No,TotalScore,BuzzScore,StillScore,VideoScore,Reason
1,95,100,93,97,"総合力も非常に高いが、特にSNSバズ度が圧倒的。静止画でも引力が強く、MV化しても主役級で動き映える。"
"""
# ---------------------------------------------------

uploaded_files = st.file_uploader(
    "画像をまとめてアップロード（最大10枚／ドラッグ＆ドロップ可）",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

if "enlarged_idx" not in st.session_state:
    st.session_state["enlarged_idx"] = None

def enlarge(idx):
    st.session_state["enlarged_idx"] = idx

def clear_enlarge():
    st.session_state["enlarged_idx"] = None

if uploaded_files:
    st.markdown("---")
    st.subheader("【ミニサムネ一覧／超高速表示】")
    images = []
    for file in uploaded_files:
        img = Image.open(file)
        img_thumb = img.copy()
        img_thumb.thumbnail((150, 150))
        images.append(img_thumb)

    NUM_COLS = 4
    thumb_width = 150
    cols = st.columns(NUM_COLS)
    for idx, img in enumerate(images):
        with cols[idx % NUM_COLS]:
            st.image(img, caption=f"Img{idx+1}", width=thumb_width)

    # --- No.連番リネームZIP一括DL ---
    st.markdown("---")
    st.subheader("No.連番リネーム画像を一括ZIP DL")
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "No_images.zip")
        for idx, file in enumerate(uploaded_files):
            img = Image.open(file)
            img_name = f"No{idx+1}.png"
            save_path = os.path.join(tmpdir, img_name)
            img.save(save_path)
        with ZipFile(zip_path, "w") as zipf:
            for idx in range(len(uploaded_files)):
                img_name = f"No{idx+1}.png"
                zipf.write(os.path.join(tmpdir, img_name), arcname=img_name)
        with open(zip_path, "rb") as f:
            st.download_button("No.連番ZIPダウンロード", f, file_name="No_images.zip")

    # --- 評価CSVテンプレDL（指示文1行目内蔵） ---
    st.markdown("---")
    st.subheader("評価CSVテンプレートDL（AI評価指示文付き）")
    eval_df = pd.DataFrame({"No": list(range(1, len(images)+1)),
                            "TotalScore": ["" for _ in images],
                            "BuzzScore": ["" for _ in images],
                            "StillScore": ["" for _ in images],
                            "VideoScore": ["" for _ in images],
                            "Reason": ["" for _ in images]})
    instruct_df = pd.DataFrame([[eval_instruction,"","","","",""]], columns=eval_df.columns)
    eval_df = pd.concat([instruct_df, eval_df], ignore_index=True)
    csv_eval = eval_df.to_csv(index=False, encoding="utf-8")
    st.download_button("評価CSVテンプレDL（指示文付き）", csv_eval, file_name="eval_template.csv", mime="text/csv")

    st.markdown("""
    **使い方:**  
    1. このCSVテンプレをダウンロード  
    2. AI（または人）が指示に従い4軸×100点＋理由で1枚ずつ独立評価→CSV記入  
    3. 下の「評価済みCSVアップロード」欄にアップ→スコア名付き画像一括DLOK
    """)

    # --- 評価済みCSVアップロード＆ZIP化 ---
    st.markdown("---")
    st.subheader("評価済みCSVアップロード（スコア＋コメント付きファイル名ZIP化・高画質サムネ/拡大）")
    eval_up = st.file_uploader("評価済みCSVをアップ", type="csv", key="evalcsvbottom")
    if eval_up:
        df_eval = pd.read_csv(eval_up)
        # 1行目が指示文の場合削除
        if not str(df_eval.iloc[0]["No"]).isdigit():
            df_eval = df_eval.iloc[1:].reset_index(drop=True)
        eval_map = {int(row['No']): row for _, row in df_eval.iterrows()}
        st.markdown("---")
        st.subheader("【評価反映サムネ一覧（高画質/拡大ボタン付）】")
        cols = st.columns(NUM_COLS)
        for idx, file in enumerate(uploaded_files):
            img = Image.open(file)
            with cols[idx % NUM_COLS]:
                st.image(img, caption="", width=400)
                if eval_map.get(idx+1) is not None:
                    e = eval_map[idx+1]
                    st.markdown(
                        f"""<div style="font-size: 13px; background:#222; border-radius:6px; color:#e4e4ff; padding:3px 8px 2px 8px; margin-top:5px; margin-bottom:10px;">
                        <b>総合:</b> {e['TotalScore']}　
                        <b>バズ:</b> {e['BuzzScore']}　
                        <b>静止画:</b> {e['StillScore']}　
                        <b>映像:</b> {e['VideoScore']}<br>
                        <b>理由:</b> {e['Reason']}
                        </div>""",
                        unsafe_allow_html=True
                    )
                    if st.button("拡大", key=f"enlarge_eval_{idx}"):
                        enlarge(idx)
                else:
                    st.markdown('<div style="height:38px"></div>', unsafe_allow_html=True)

        if st.session_state["enlarged_idx"] is not None:
            eidx = st.session_state["enlarged_idx"]
            img_big = Image.open(uploaded_files[eidx])
            st.markdown("---")
            st.markdown(f"### 🟢 高画質最大表示")
            st.image(img_big, use_column_width=True)
            if st.button("拡大を閉じる", key="close_enlarge_eval"):
                clear_enlarge()

        # スコア＋コメント付きファイル名ZIPダウンロード
        st.markdown("---")
        st.subheader("4軸スコア＋コメント付きファイル名画像を一括ZIP DL")
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "Eval_named_images.zip")
            with ZipFile(zip_path, "w") as zipf:
                for idx, file in enumerate(uploaded_files):
                    img = Image.open(file)
                    e = eval_map.get(idx+1, {})
                    total = str(e.get("TotalScore", ""))
                    buzz = str(e.get("BuzzScore", ""))
                    still = str(e.get("StillScore", ""))
                    video = str(e.get("VideoScore", ""))
                    reason = str(e.get("Reason", ""))
                    def clean(s):
                        s = str(s)
                        s = s.replace("/", "／").replace("\\", "＼").replace(":", "：").replace("*", "＊")
                        s = s.replace("?", "？").replace('"', "”").replace("<", "＜").replace(">", "＞").replace("|", "｜")
                        s = s.replace(" ", "_").replace("\n", "")
                        return s[:30]
                    img_name = f"{total}_{buzz}_{still}_{video}_{clean(reason)}.png"
                    save_path = os.path.join(tmpdir, img_name)
                    img.save(save_path)
                    zipf.write(save_path, arcname=img_name)
            with open(zip_path, "rb") as f:
                st.download_button("スコア＋コメント名ZIPダウンロード", f, file_name="Eval_named_images.zip")
else:
    st.info("画像をアップロードしてください。")
