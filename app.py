import streamlit as st
from PIL import Image
import pandas as pd
import tempfile
import os
from zipfile import ZipFile
import io

st.set_page_config(layout="wide")
st.title("AI画像評価システム｜No連番サムネ・増殖ゼロ・完全一致版")

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

def get_no_filename(idx):
    return f"No{idx+1}.png"

if uploaded_files:
    st.markdown("---")
    st.subheader("【ミニサムネ一覧／No連番のみ表示】")
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
        no_fname = get_no_filename(idx)
        with cols[idx % NUM_COLS]:
            st.image(img, caption=no_fname, width=thumb_width)

    # --- No.連番リネームZIP一括DL ---
    st.markdown("---")
    st.subheader("No.連番リネーム画像を一括ZIP DL")
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "No_images.zip")
        for idx, file in enumerate(uploaded_files):
            img = Image.open(file)
            img_name = get_no_filename(idx)
            save_path = os.path.join(tmpdir, img_name)
            img.save(save_path)
        with ZipFile(zip_path, "w") as zipf:
            for idx in range(len(uploaded_files)):
                img_name = get_no_filename(idx)
                zipf.write(os.path.join(tmpdir, img_name), arcname=img_name)
        with open(zip_path, "rb") as f:
            st.download_button("No.連番ZIPダウンロード", f, file_name="No_images.zip")

    # --- AI評価プロンプト ---
    st.markdown("---")
    st.markdown("## 🟣【AI評価プロンプト（No連番画像専用）】")
    ai_prompt = """あなたはAI画像審査員です。

【評価ルール】
- 各画像は「No1.png, No2.png, ...」のファイル名で完全独立絶対評価してください。
- 評価CSVはFileName主キーのみ。No列や元名列は不要。
- Reason欄には点数根拠・短所も具体的に明記。

【出力フォーマット】
FileName,TotalScore,BuzzScore,StillScore,VideoScore,Reason

- FileNameには「No1.png」など連番ファイル名を必ず記載してください（拡張子・大文字小文字・空白含め完全一致）。
- CSVは1行目ヘッダー、以降は画像ごと1行。
"""
    st.code(ai_prompt, language="markdown")

    # --- 評価済みCSV入力エリア（アップ & コピペ両対応）---
    st.markdown("---")
    st.markdown("### 🟢【AI評価CSVのアップロード or コピペ入力】")
    eval_up = st.file_uploader("評価済みCSVをアップロード（FileName主キーでNo列不要）", type="csv", key="evalcsvbottom")
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
        st.subheader("【評価反映サムネ一覧（No連番名・拡大ボタン付）】")
        eval_map = {row["FileName"].strip(): row for _, row in df_eval.iterrows()}
        for idx, img in enumerate(images):
            no_fname = get_no_filename(idx)
            with cols[idx % NUM_COLS]:
                st.image(img, caption=no_fname, width=thumb_width)
                if no_fname in eval_map:
                    e = eval_map[no_fname]
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
            st.image(img_big, use_column_width=True)
            if st.button("拡大を閉じる", key="close_enlarge_eval"):
                clear_enlarge()
                st.experimental_rerun()

        # スコア＋コメント付きファイル名ZIPダウンロード
        st.markdown("---")
        st.subheader("4軸スコア＋コメント付きファイル名画像を一括ZIP DL")
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "Eval_named_images.zip")
            with ZipFile(zip_path, "w") as zipf:
                for idx, file in enumerate(uploaded_files):
                    img = Image.open(file)
                    no_fname = get_no_filename(idx)
                    e = eval_map.get(no_fname, {})
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
                    img_name = f"{no_fname}_{total}_{buzz}_{still}_{video}_{clean(reason)}.png"
                    save_path = os.path.join(tmpdir, img_name)
                    img.save(save_path)
                    zipf.write(save_path, arcname=img_name)
            with open(zip_path, "rb") as f:
                st.download_button("スコア＋コメント名ZIPダウンロード", f, file_name="Eval_named_images.zip")
else:
    st.info("画像をアップロードしてください。")
