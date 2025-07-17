import streamlit as st
from PIL import Image
import pandas as pd
import tempfile
import os
from zipfile import ZipFile
import unicodedata
import io

st.set_page_config(layout="wide")
st.title("AI画像評価システム｜完全版")

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

# アップロード画像→No連番
images = []
filenames = []
if uploaded_files:
    for idx, file in enumerate(uploaded_files):
        img = Image.open(file)
        img_thumb = img.copy()
        img_thumb.thumbnail((200, 200))
        images.append(img_thumb)
        filenames.append(f"No{idx+1}.png")
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

    # --- AI評価プロンプト表示（絶対変更禁止） ---
    st.markdown("---")
    st.markdown("## 🟣【AI評価プロンプト（ChatGPT等にコピペ→Noリネーム画像を必ず渡す）】")
    ai_prompt = """あなたはAI画像審査員です。

【評価ルール】
- 画像は「1枚ごとに完全独立」かつ「絶対評価」「１００点満点」で採点してください。他画像との比較や相対減点は禁止です。
- 評価CSVはFileName主キーとし、No列や順位列は不要です。
- Reason欄には各点数の理由・強み・短所も必ず明記。
- 出力は下記形式を厳守。

【出力フォーマット】
FileName,TotalScore,BuzzScore,StillScore,VideoScore,Reason

- FileNameには評価対象画像のファイル名（例：No3.png）を正確に記載してください（拡張子まで完全一致）。
- どんな場合もFileName列には、画像そのもののファイル名（例：No3.png）を必ず書いてください。
- 画像のアップ順や表示順に関係なく、ファイル名が唯一の評価キーになります。
- 評価内容は各画像で完全独立（比較や連動点数は禁止）。
- CSV形式（カンマ区切り）で出力し、必ず一行目がヘッダーになるようにしてください。
"""
    st.code(ai_prompt, language="markdown")

    # --- 評価CSVアップ & コピペ両対応 ---
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

    # --- 評価反映サムネ＆拡大・一括DL機能 ---
    if df_eval is not None:
        st.markdown("---")
        st.subheader("【評価反映サムネ一覧（2カラム×4行／高画質ソート／拡大付）】")

        # ソート用辞書：ファイル名→idx
        fname2idx = {f"No{idx+1}.png": idx for idx in range(len(uploaded_files))}
        df_eval["TotalScore"] = pd.to_numeric(df_eval["TotalScore"], errors="coerce")
        df_eval_sorted = df_eval.sort_values(by="TotalScore", ascending=False)
        sorted_items = []
        for _, row in df_eval_sorted.iterrows():
            fname = row["FileName"]
            idx = fname2idx.get(fname)
            if idx is not None:
                sorted_items.append((idx, row))

        eval_cols = st.columns(2)
        for i, (img_idx, e) in enumerate(sorted_items):
            col = eval_cols[i % 2]
            with col:
                img = Image.open(uploaded_files[img_idx])
                st.image(img, caption=f"{e['FileName']}", use_container_width=True)
                st.markdown(
                    f"""<div style="font-size: 15px; background:#222; border-radius:8px; color:#e4e4ff; padding:6px 14px 4px 14px; margin-top:10px; margin-bottom:14px;">
                    <b>総合:</b> {e['TotalScore']}　
                    <b>バズ:</b> {e['BuzzScore']}　
                    <b>静止画:</b> {e['StillScore']}　
                    <b>映像:</b> {e['VideoScore']}<br>
                    <b>理由:</b> {e['Reason']}
                    </div>""",
                    unsafe_allow_html=True
                )
                if st.button("拡大", key=f"enlarge_eval_{img_idx}"):
                    enlarge(img_idx)

        # 拡大サムネ（ワンクリックで消す・return禁止！）
        if st.session_state["enlarged_idx"] is not None:
            eidx = st.session_state["enlarged_idx"]
            img_big = Image.open(uploaded_files[eidx])
            st.markdown("---")
            st.markdown(f"### 🟢 高画質最大表示")
            st.image(img_big, use_container_width=True)
            if st.button("拡大を閉じる", key="close_enlarge_eval"):
                clear_enlarge()

        # スコア＋コメント付きファイル名画像を一括ZIP DL
        st.markdown("---")
        st.subheader("4軸スコア＋コメント付きファイル名画像を一括ZIP DL")
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "Eval_named_images.zip")
            with ZipFile(zip_path, "w") as zipf:
                for idx, file in enumerate(uploaded_files):
                    img = Image.open(file)
                    fname = f"No{idx+1}.png"
                    key = clean_filename(fname)
                    e = df_eval.set_index("FileName").to_dict("index").get(fname, {})
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
