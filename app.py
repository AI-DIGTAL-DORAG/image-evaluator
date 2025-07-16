import streamlit as st
from PIL import Image
import pandas as pd
import tempfile
import os
from zipfile import ZipFile
import unicodedata
import io

st.set_page_config(layout="wide")
st.title("AI画像評価システム｜FileName一致・CSVコピペ/アップ両対応・完全版")

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

# --- 評価データ入力欄（アップ or コピペ） ---
df_eval = None
st.markdown("### 🟢【AI評価CSVアップ or コピペ】")
eval_up = st.file_uploader("評価済みCSVファイルをアップ（推奨：FileName主キーでNo列なし）", type="csv", key="evalcsvbottom")
csv_text = st.text_area("AIが返した評価CSVをそのままコピペ（FileName,TotalScore,BuzzScore,StillScore,VideoScore,Reason）", height=150)

if eval_up:
    df_eval = pd.read_csv(eval_up)
elif csv_text:
    try:
        df_eval = pd.read_csv(io.StringIO(csv_text))
    except Exception as e:
        st.warning("CSVの書式エラーまたは貼り付け内容不備")

if uploaded_files:
    st.markdown("---")
    st.subheader("【評価反映サムネ一覧（ファイル名マッチ・拡大ボタン付）】")
    images = []
    filenames = []
    for file in uploaded_files:
        img = Image.open(file)
        img_thumb = img.copy()
        img_thumb.thumbnail((150, 150))
        images.append(img_thumb)
        filenames.append(os.path.basename(file.name))

    NUM_COLS = 4
    thumb_width = 150
    cols = st.columns(NUM_COLS)
    # 評価マップ（ファイル名クリーン化マッチ！）
    eval_map = {}
    if df_eval is not None:
        for _, row in df_eval.iterrows():
            fname = clean_filename(row["FileName"])
            eval_map[fname] = row

    for idx, (img, fname_raw) in enumerate(zip(images, filenames)):
        fname = clean_filename(fname_raw)
        with cols[idx % NUM_COLS]:
            st.image(img, width=thumb_width)
            # ファイル名を下に小さく表示
            st.caption(fname_raw)
            # 評価内容表示
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
        st.image(img_big, use_column_width=True)
        if st.button("拡大を閉じる", key="close_enlarge_eval"):
            clear_enlarge()
            st.experimental_rerun()
else:
    st.info("画像をアップロードしてください。")
