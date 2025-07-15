import streamlit as st
from PIL import Image
import pandas as pd
import tempfile
import os
import base64
import shutil
from zipfile import ZipFile

st.set_page_config(layout="wide")
st.title("画像No.自動付与＆評価システム｜4カラム400px最新版")

st.markdown("""
⬇️ 評価フロー  
1. 画像をまとめてアップロード  
2. No.自動付与サムネ一覧（4カラム×400px幅で絶対被らない）  
3. 各サムネ下に「原寸DL」・「↓拡大」ボタン  
4. 拡大時は下部で最大表示（原寸DL可、拡大解除もOK）  
5. 画像全体をNo連番ファイル名で一括ZIP DL  
6. 評価CSVテンプレDL・アップロード  
""")

uploaded_files = st.file_uploader(
    "画像をまとめてアップロード（ドラッグ＆ドロップ可）",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

# Session state for enlarged view
if "enlarged_idx" not in st.session_state:
    st.session_state["enlarged_idx"] = None

def enlarge(idx):
    st.session_state["enlarged_idx"] = idx

def clear_enlarge():
    st.session_state["enlarged_idx"] = None

if uploaded_files:
    st.markdown("---")
    st.subheader("サムネ一覧（4カラム×400px／No.自動付与・被りゼロ）")

    images = []
    filemap = {}
    for idx, file in enumerate(uploaded_files):
        img = Image.open(file)
        images.append(img.copy())
        filemap[idx+1] = file.name  # No: FileName

    # サムネ表示（4カラム×400px）
    NUM_COLS = 4
    thumb_width = 400
    cols = st.columns(NUM_COLS)
    for idx, img in enumerate(images):
        with cols[idx % NUM_COLS]:
            st.image(img, caption=f"No.{idx+1}", width=thumb_width)
            # 原寸DLボタン
            buf = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            img.save(buf, format="PNG")
            buf.close()
            with open(buf.name, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode()
            dl_link = f'<a href="data:image/png;base64,{b64_img}" download="No{idx+1}.png">原寸DL</a>'
            st.markdown(dl_link, unsafe_allow_html=True)
            # 拡大ボタン
            if st.button("↓拡大", key=f"enlarge_{idx}"):
                enlarge(idx)

    # 下部最大化表示エリア
    if st.session_state["enlarged_idx"] is not None:
        eidx = st.session_state["enlarged_idx"]
        st.markdown("---")
        st.markdown(f"### 🟢 No.{eidx+1} 最大表示（原寸 or use_column_width）")
        st.image(images[eidx], use_column_width=True)
        # 原寸DLボタン
        buf2 = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        images[eidx].save(buf2, format="PNG")
        buf2.close()
        with open(buf2.name, "rb") as f:
            b64_img2 = base64.b64encode(f.read()).decode()
        dl_link2 = f'<a href="data:image/png;base64,{b64_img2}" download="No{eidx+1}.png">原寸DL</a>'
        st.markdown(dl_link2, unsafe_allow_html=True)
        if st.button("拡大を閉じる"):
            clear_enlarge()

    # 一括No.連番リネーム＋ZIPダウンロード
    st.markdown("---")
    st.subheader("No.連番リネーム画像を一括ZIP DL")
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "No_images.zip")
        with ZipFile(zip_path, "w") as zipf:
            for idx, img in enumerate(images):
                img_name = f"No{idx+1}.png"
                save_path = os.path.join(tmpdir, img_name)
                img.save(save_path)
                zipf.write(save_path, arcname=img_name)
        with open(zip_path, "rb") as f:
            st.download_button("No.連番ZIPダウンロード", f, file_name="No_images.zip")

    # 評価CSVテンプレDL（AI評価用No.管理雛形）
    st.markdown("---")
    st.subheader("評価CSVテンプレートDL（AI/人間評価用）")
    eval_df = pd.DataFrame({"No": list(range(1, len(images)+1)),
                            "BuzzScore": ["" for _ in images],
                            "StillScore": ["" for _ in images],
                            "VideoScore": ["" for _ in images],
                            "Reason": ["" for _ in images],
                            "TotalScore": ["" for _ in images]})
    csv_eval = eval_df.to_csv(index=False).encode("utf-8")
    st.download_button("評価CSVテンプレDL", csv_eval, file_name="eval_template.csv", mime="text/csv")

    st.markdown("""
    **評価ルール・プロンプト例（CSVやAI依頼時に添付）**  
    - Noで指定した画像を「独立に」バズ期待値・静止画スコア・映像適性・理由・総合スコアで評価  
    - BuzzScore: high/medium/low（点換算10/7/3）  
    - StillScore: 1～10点  
    - VideoScore: 1star～5star（点換算2～10）  
    - Reason: 短い日本語コメント  
    - TotalScore: (BuzzScore点＋StillScore＋VideoScore点)/3（小数点1桁）
    """)

    # 評価CSVアップロード＆内容表示（紐付け確認）
    st.markdown("---")
    st.subheader("評価CSVをアップロード（Noで自動紐付け・確認用）")
    eval_up = st.file_uploader("評価済みCSVをアップ", type="csv", key="evalcsv")
    if eval_up:
        df_eval = pd.read_csv(eval_up)
        st.write(df_eval)

else:
    st.info("画像をアップロードしてください。")
