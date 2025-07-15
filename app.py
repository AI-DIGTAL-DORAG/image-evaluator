import streamlit as st
from PIL import Image
import pandas as pd
import tempfile
import os
from zipfile import ZipFile

st.set_page_config(layout="wide")
st.title("AI画像評価システム｜4軸100点評価＋コメントZIP完全版")

st.markdown("""
⬇️ 評価フロー  
1. 画像をまとめてアップロード（ドラッグ＆ドロップ可）  
2. ミニサムネ（4カラム×150px幅）で高速一覧  
3. 【1行目AI審査プロンプト入り】評価CSVテンプレDL  
4. 最下部で評価済みCSVアップロード  
5. スコア＋コメント付きファイル名で一括ZIPダウンロード  
6. 評価反映後のみ高画質サムネ＆拡大ボタン
""")

uploaded_files = st.file_uploader(
    "画像をまとめてアップロード（ドラッグ＆ドロップ可）",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

if "enlarged_idx" not in st.session_state:
    st.session_state["enlarged_idx"] = None

def enlarge(idx):
    st.session_state["enlarged_idx"] = idx

def clear_enlarge():
    st.session_state["enlarged_idx"] = None

# ==== AI審査プロンプト（1行目テンプレ用）====
eval_instruction = """【AI画像審査プロンプト】
あなたはAI画像やSNS映像作品の審査員です。
各画像を“絶対評価”で下記4項目（各100点満点）で明確に分けて評価してください。
重複なく、各軸の定義を明示し、各項目の理由もコメントに必ず分けて書いてください。

1. 総合スコア（TotalScore／100点満点）
静止画、映像化、技術、唯一性、世界観、物語性など“すべて”の要素を総合的に採点。

2. BuzzScore（バズ期待値／100点満点）
SNS・サムネで“一発バズる起爆力・拡散力”のみを評価。

3. StillScore（静止画スコア／100点満点）
一枚絵の美しさ・構図・色彩・唯一性等“静止画としての完成度”を評価。

4. VideoScore（映像適性スコア／100点満点）
SORAやMV化した際に“どれだけ動きやすいか、映像で映えるか”を評価。

Reason（各項目ごとに、なぜその得点になったかを必ずコメント）
必ず4項目を明確に分けて絶対評価し、No,TotalScore,BuzzScore,StillScore,VideoScore,ReasonのCSV形式で出力。
"""
# ===============================================

eval_map = {}

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

    # --- 評価CSVテンプレDL（AI審査プロンプト入り） ---
    st.markdown("---")
    st.subheader("評価CSVテンプレートDL（AI審査プロンプト付き）")
    eval_df = pd.DataFrame({"No": list(range(1, len(images)+1)),
                            "TotalScore": ["" for _ in images],
                            "BuzzScore": ["" for _ in images],
                            "StillScore": ["" for _ in images],
                            "VideoScore": ["" for _ in images],
                            "Reason": ["" for _ in images]})
    instruct_df = pd.DataFrame([[eval_instruction,"","","","",""]], columns=eval_df.columns)
    eval_df = pd.concat([instruct_df, eval_df], ignore_index=True)
    csv_eval = eval_df.to_csv(index=False, encoding="utf-8")
    st.download_button("評価CSVテンプレDL（審査プロンプト付き）", csv_eval, file_name="eval_template.csv", mime="text/csv")

    st.markdown("""
    **評価ルール・プロンプト例（CSVやAI依頼時に添付）**  
    - No,TotalScore,BuzzScore,StillScore,VideoScore,Reason
    - すべて100点満点絶対評価＆コメント必須
    """)

    # === 評価済みCSVアップロード＋スコア＋コメント付きファイル名ZIP ===
    st.markdown("---")
    st.subheader("評価済みCSVアップロード（4軸スコア＋コメント付きファイル名ZIP化・高画質サムネ/拡大）")
    eval_up = st.file_uploader("評価済みCSVをアップ", type="csv", key="evalcsvbottom", help="アップロードでスコア付きファイル名ZIP＆高画質サムネ・拡大可能")
    if eval_up:
        df_eval = pd.read_csv(eval_up)
        eval_map = {int(row['No']): row for _, row in df_eval.iterrows()}

        # 高画質サムネ＋スコア・拡大
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

        # 拡大表示エリア（評価反映時のみ）
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
                    # NG文字クリーニング＋30字制限
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
