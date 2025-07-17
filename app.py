import streamlit as st
from PIL import Image
import pandas as pd
import tempfile
import os
from zipfile import ZipFile
import unicodedata
import io

st.set_page_config(layout="wide")
st.title("AI画像評価システム｜Noリネーム主軸・絶対ズレない完全版")

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

def clean_filename(s):
    s = str(s)
    s = s.strip().replace(" ", "").replace("　", "").replace("\n", "").replace("\t", "")
    s = unicodedata.normalize("NFKC", s)
    return s.lower()

# 1. 画像アップロード→Noリネーム基軸配列構築
images = []
filenames = []
if uploaded_files:
    for idx, file in enumerate(uploaded_files):
        img = Image.open(file)
        img_thumb = img.copy()
        img_thumb.thumbnail((200, 200))  # ミニサムネは固定サイズ
        images.append(img_thumb)
        filenames.append(f"No{idx+1}.png")  # 強制No連番
else:
    images = []
    filenames = []

NUM_COLS = 4
thumb_width = 200

if uploaded_files:
    st.markdown("---")
    st.subheader("【ミニサムネ一覧／Noリネーム名で表示】")
    cols = st.columns(NUM_COLS)
    for idx, (img, fname) in enumerate(zip(images, filenames)):
        with cols[idx % NUM_COLS]:
            st.image(img, caption=f"{fname}", width=thumb_width)

    # --- No.連番リネームZIP一括DL（100%No1.png～No10.png） ---
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

    # --- AI評価プロンプト表示（Noリネーム名で渡せと明示） ---
    st.markdown("---")
    st.markdown("## 🟣【AI評価プロンプト（ChatGPT等にコピペ→Noリネーム画像を必ず渡す）】")
    ai_prompt = """あなたはAI画像審査員です。

【評価ルール】
- 必ずNo1.png, No2.png…というファイル名で画像が渡されます（例：No3.png）。
- FileNameにはそのファイル名（NoX.png）を必ず記載し、他カラムも各画像ごとに記入してください。
- 評価は1枚ごとに完全独立、比較や相対評価は禁止。
- 出力は下記形式を厳守。

【出力フォーマット】
FileName,TotalScore,BuzzScore,StillScore,VideoScore,Reason

例：
FileName,TotalScore,BuzzScore,StillScore,VideoScore,Reason
No1.png,98,96,94,97,"バズ度・映像化適性とも最高。"
No2.png,92,89,91,90,"構図・色彩優秀、バズは普通。"
"""
    st.code(ai_prompt, language="markdown")

    # --- 評価CSVアップ & コピペ両対応、完全No主キー ---
    st.markdown("---")
    st.markdown("### 🟢【AI評価CSVのアップロード or コピペ入力】")
    eval_up = st.file_uploader("評価済みCSV（FileName列＝Noリネーム名のみ）", type="csv", key="evalcsvbottom")
    csv_text = st.text_area("AIが返した評価CSVをそのままコピペ（FileName,TotalScore,BuzzScore,StillScore,VideoScore,Reason）", height=150)
    df_eval = None
    if eval_up:
        df_eval = pd.read_csv(eval_up)
    elif csv_text:
        try:
            df_eval = pd.read_csv(io.StringIO(csv_text))
        except Exception as e:
            st.warning("CSVの書式エラーまたは貼り付け内容不備")

    # --- 評価反映サムネ＆拡大・一括DL機能（絶対No連番でマッチ） ---
    if df_eval is not None:
        st.markdown("---")
        st.subheader("【評価反映サムネ一覧（No連番・拡大付・絶対ズレない）】")
        eval_map = {clean_filename(row["FileName"]): row for _, row in df_eval.iterrows()}
        cols = st.columns(NUM_COLS)
        for idx, (img, fname) in enumerate(zip(images, filenames)):
            key = clean_filename(fname)
            with cols[idx % NUM_COLS]:
                st.image(img, caption=f"{fname}", width=thumb_width)
                if key in eval_map:
                    e = eval_map[key]
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
        # 拡大サムネ：閉じるボタンで消す
        if st.session_state["enlarged_idx"] is not None:
            eidx = st.session_state["enlarged_idx"]
            img_big = Image.open(uploaded_files[eidx])
            st.markdown("---")
            st.markdown(f"### 🟢 高画質最大表示")
            st.image(img_big, use_container_width=True)
            if st.button("拡大を閉じる", key="close_enlarge_eval"):
                clear_enlarge()
                st.experimental_rerun()

        # スコア＋コメント付きファイル名画像を一括ZIP DL（No連番強制）
        st.markdown("---")
        st.subheader("4軸スコア＋コメント付きファイル名画像を一括ZIP DL")
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "Eval_named_images.zip")
            with ZipFile(zip_path, "w") as zipf:
                for idx, file in enumerate(uploaded_files):
                    img = Image.open(file)
                    fname = f"No{idx+1}.png"
                    key = clean_filename(fname)
                    e = eval_map.get(key, {})
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
                    img_name = f"No{idx+1}_{total}_{buzz}_{still}_{video}_{clean(reason)}.png"
                    save_path = os.path.join(tmpdir, img_name)
                    img.save(save_path)
                    zipf.write(save_path, arcname=img_name)
            with open(zip_path, "rb") as f:
                st.download_button("スコア＋コメント名ZIPダウンロード", f, file_name="Eval_named_images.zip")

else:
    st.info("画像をアップロードしてください。")
