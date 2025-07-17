import streamlit as st
from PIL import Image
import pandas as pd
import tempfile
import os
from zipfile import ZipFile
import unicodedata
import io

st.set_page_config(layout="wide")
st.title("AI画像評価システム｜No連番サムネ・FileName主キー・高画質2カラム完全版")

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

if uploaded_files:
    st.markdown("---")
    st.subheader("【ミニサムネ一覧／No連番＋ファイル名表示】")
    images = []
    filenames = []
    for file in uploaded_files:
        img = Image.open(file)
        img_thumb = img.copy()
        img_thumb.thumbnail((400, 400))  # 大きめサムネ
        images.append(img_thumb)
        filenames.append(os.path.basename(file.name))

    NUM_COLS = 2  # 2カラム×4行
    thumb_width = 400
    rows = (len(images) + NUM_COLS - 1) // NUM_COLS
    cols = st.columns(NUM_COLS)
    for row in range(rows):
        for col in range(NUM_COLS):
            idx = row * NUM_COLS + col
            if idx < len(images):
                with cols[col]:
                    st.image(images[idx], caption=f"No{idx+1} / {filenames[idx]}", width=thumb_width)

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

    # --- AI評価プロンプト現場表示 ---
    st.markdown("---")
    st.markdown("## 🟣【AI評価プロンプト（ChatGPT等にコピペ→Noリネーム画像を渡す）】")
    ai_prompt = """あなたはAI画像審査員です。

【評価ルール】
- 画像は「1枚ごとに完全独立」かつ「絶対評価」で採点してください。他画像との比較や相対減点は禁止です。
- 評価CSVはFileName主キーとし、No列や順位列は不要です。
- Reason欄には各点数の理由・強み・短所も必ず明記。
- 出力は下記形式を厳守。

【出力フォーマット】
FileName,TotalScore,BuzzScore,StillScore,VideoScore,Reason

- FileNameには評価対象画像のファイル名（例：No3.png）を正確に記載してください（拡張子まで完全一致）。
- 評価内容は各画像で完全独立（比較や連動点数は禁止）。
- CSV形式（カンマ区切り）で出力し、必ず一行目がヘッダーになるようにしてください。
"""
    st.code(ai_prompt, language="markdown")

    # --- 評価済みCSV入力エリア（アップ & コピペ両対応）---
    st.markdown("---")
    st.markdown("### 🟢【AI評価CSVのアップロード or コピペ入力】")
    eval_up = st.file_uploader("評価済みCSVをアップロード（FileName主キーでNo列なし）", type="csv", key="evalcsvbottom")
    csv_text = st.text_area("AIが返した評価CSVをそのままコピペ（FileName,TotalScore,BuzzScore,StillScore,VideoScore,Reason）", height=150)
    df_eval = None
    if eval_up:
        df_eval = pd.read_csv(eval_up)
    elif csv_text:
        try:
            df_eval = pd.read_csv(io.StringIO(csv_text))
        except Exception as e:
            st.warning("CSVの書式エラーまたは貼り付け内容不備")

    # --- 評価反映サムネ＆拡大・一括DL機能 ---
    if df_eval is not None:
        st.markdown("---")
        st.subheader("【評価反映サムネ一覧（No連番＋ファイル名・拡大ボタン付／高画質2カラム）】")
        eval_map = {clean_filename(row["FileName"]): row for _, row in df_eval.iterrows()}
        # 2カラムx4行の評価サムネ
        rows = (len(images) + NUM_COLS - 1) // NUM_COLS
        eval_cols = st.columns(NUM_COLS)
        for row in range(rows):
            for col in range(NUM_COLS):
                idx = row * NUM_COLS + col
                if idx < len(images):
                    fname_raw = filenames[idx]
                    fname = clean_filename(fname_raw)
                    with eval_cols[col]:
                        st.image(images[idx], caption=f"No{idx+1} / {fname_raw}", width=thumb_width, use_container_width=True)
                        if fname in eval_map:
                            e = eval_map[fname]
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
                # 「rerun」ではなくreturnで再レンダリング（エラー防止）
                st.stop()

        # スコア＋コメント付きファイル名ZIPダウンロード
        st.markdown("---")
        st.subheader("4軸スコア＋コメント付きファイル名画像を一括ZIP DL")
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "Eval_named_images.zip")
            with ZipFile(zip_path, "w") as zipf:
                for idx, file in enumerate(uploaded_files):
                    img = Image.open(file)
                    fname = clean_filename(os.path.basename(file.name))
                    e = eval_map.get(fname, {})
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
