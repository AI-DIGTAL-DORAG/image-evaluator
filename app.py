import streamlit as st
from PIL import Image
import pandas as pd
import tempfile
import os
import base64
from zipfile import ZipFile

st.set_page_config(layout="wide")
st.title("画像No.自動付与＆評価システム｜ミニサムネ＋評価反映で高画質 完全版")

st.markdown("""
⬇️ 評価フロー  
1. 画像をまとめてアップロード  
2. ミニサムネ（低画質・軽量）4カラム並びで超速一覧  
3. 評価CSVテンプレDL（AI評価指示文入り）  
4. 一番下で評価済みCSVアップロード  
5. 高画質サムネ＋点数付きファイル名ZIP一括DL  
6. 評価反映後だけ「拡大」ボタン（サムネ下）で高画質個別最大化
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

# -------------------評価指示-------------------------
eval_instruction = """【AI評価指示文（コピペ用）】
各画像を「独立に」評価してください。比較や順番、ファイル名の類似などは一切考慮しないでください。
No, BuzzScore, StillScore, VideoScore, Reason, TotalScoreの6列でCSV出力してください。
- BuzzScore: high/medium/low（点換算10/7/3）
- StillScore: 1～10点
- VideoScore: 1star～5star（点換算2～10）
- Reason: 短い日本語コメント
- TotalScore: (BuzzScore点＋StillScore＋VideoScore点)/3（小数点1桁）
例: 1,high,8,5star,まるで現実のような美しさ,9.3
"""
# ---------------------------------------------------

# 評価マップ仮置き
eval_map = {}

if uploaded_files:
    st.markdown("---")
    st.subheader("【ミニサムネ一覧／No.自動付与・超高速表示】")

    images = []
    filemap = {}
    for idx, file in enumerate(uploaded_files):
        img = Image.open(file)
        # サムネ用に小さく変換（例：150px幅・JPEG圧縮）
        img_thumb = img.copy()
        img_thumb.thumbnail((150, 150))
        images.append(img_thumb)
        filemap[idx+1] = file.name  # No: FileName

    NUM_COLS = 4
    thumb_width = 150  # ミニサムネ
    cols = st.columns(NUM_COLS)
    for idx, img in enumerate(images):
        with cols[idx % NUM_COLS]:
            st.image(img, caption=f"No.{idx+1}", width=thumb_width)

    # 評価CSVテンプレDL（AI評価指示文入り）
    st.markdown("---")
    st.subheader("評価CSVテンプレートDL（AI評価指示文付き）")
    eval_df = pd.DataFrame({"No": list(range(1, len(images)+1)),
                            "BuzzScore": ["" for _ in images],
                            "StillScore": ["" for _ in images],
                            "VideoScore": ["" for _ in images],
                            "Reason": ["" for _ in images],
                            "TotalScore": ["" for _ in images]})
    instruct_df = pd.DataFrame([[eval_instruction,"","","","",""]], columns=eval_df.columns)
    eval_df = pd.concat([instruct_df, eval_df], ignore_index=True)
    csv_eval = eval_df.to_csv(index=False, encoding="utf-8")
    st.download_button("評価CSVテンプレDL（指示文付き）", csv_eval, file_name="eval_template.csv", mime="text/csv")

    st.markdown("""
    **評価ルール・プロンプト例（CSVやAI依頼時に添付）**  
    - Noで指定した画像を「独立に」バズ期待値・静止画スコア・映像適性・理由・総合スコアで評価  
    - BuzzScore: high/medium/low（点換算10/7/3）  
    - StillScore: 1～10点  
    - VideoScore: 1star～5star（点換算2～10）  
    - Reason: 短い日本語コメント  
    - TotalScore: (BuzzScore点＋StillScore＋VideoScore点)/3（小数点1桁）
    """)

    # ====== 下部：評価済みCSVアップロード＋スコア反映・高画質拡大・ファイル名付きZIP ======
    st.markdown("---")
    st.subheader("評価済みCSVアップロード（スコア反映＆高画質サムネ＋拡大＋ファイル名付きZIP化）")
    eval_up = st.file_uploader("評価済みCSVをアップ", type="csv", key="evalcsvbottom", help="アップロードでスコア付きサムネ＆高画質DL可能に")
    if eval_up:
        df_eval = pd.read_csv(eval_up)
        eval_map = {int(row['No']): row for _, row in df_eval.iterrows()}

        # 再度「高画質サムネ＋スコア」で再描画
        st.markdown("---")
        st.subheader("【評価反映サムネ一覧（高画質/拡大ボタン付）】")
        # 高画質画像に差し替え
        cols = st.columns(NUM_COLS)
        for idx, file in enumerate(uploaded_files):
            img = Image.open(file)
            with cols[idx % NUM_COLS]:
                st.image(img, caption=f"No.{idx+1}", width=400)
                # 評価結果表示
                if eval_map.get(idx+1) is not None:
                    e = eval_map[idx+1]
                    st.markdown(
                        f"""<div style="font-size: 13px; background:#222; border-radius:6px; color:#e4e4ff; padding:3px 8px 2px 8px; margin-top:5px; margin-bottom:10px;">
                        <b>バズ期待値:</b> {e['BuzzScore']}　
                        <b>静止画:</b> {e['StillScore']}　
                        <b>映像適性:</b> {e['VideoScore']}<br>
                        <b>総合スコア:</b> {e['TotalScore']}<br>
                        <b>理由:</b> {e['Reason']}
                        </div>""",
                        unsafe_allow_html=True
                    )
                    # 拡大（最大化）ボタン
                    if st.button("拡大", key=f"enlarge_eval_{idx}"):
                        enlarge(idx)
                else:
                    st.markdown('<div style="height:38px"></div>', unsafe_allow_html=True)

        # 拡大表示エリア（評価反映時のみ）
        if st.session_state["enlarged_idx"] is not None:
            eidx = st.session_state["enlarged_idx"]
            img_big = Image.open(uploaded_files[eidx])
            st.markdown("---")
            st.markdown(f"### 🟢 No.{eidx+1} 高画質最大表示")
            st.image(img_big, use_column_width=True)
            if st.button("拡大を閉じる", key="close_enlarge_eval"):
                clear_enlarge()

        # 評価スコア付きファイル名ZIPダウンロード
        st.markdown("---")
        st.subheader("評価スコア付きファイル名画像を一括ZIP DL")
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "Eval_named_images.zip")
            with ZipFile(zip_path, "w") as zipf:
                for idx, file in enumerate(uploaded_files):
                    img = Image.open(file)
                    e = eval_map.get(idx+1, {})
                    buzz = str(e.get("BuzzScore", ""))
                    still = str(e.get("StillScore", ""))
                    video = str(e.get("VideoScore", ""))
                    total = str(e.get("TotalScore", ""))
                    def clean(s):
                        return str(s).replace("/", "-").replace("\\", "-").replace(" ", "_")
                    img_name = f"No{idx+1}_{clean(buzz)}_{clean(still)}_{clean(video)}_{clean(total)}.png"
                    save_path = os.path.join(tmpdir, img_name)
                    img.save(save_path)
                    zipf.write(save_path, arcname=img_name)
            with open(zip_path, "rb") as f:
                st.download_button("評価名入りZIPダウンロード", f, file_name="Eval_named_images.zip")
else:
    st.info("画像をアップロードしてください。")
