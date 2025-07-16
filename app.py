import streamlit as st
from PIL import Image
import pandas as pd
import tempfile
import os
from zipfile import ZipFile

st.set_page_config(layout="wide")
st.title("AI画像評価システム｜ファイル名一致・AI評価フロー完全版")

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
    st.subheader("【ミニサムネ一覧／ファイル名表示】")
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

    # --- AIプロンプト＋半自動運用ガイド＋ファイル名カラム仕様 ---
    st.markdown("---")
    st.markdown("## 🟣【AI評価プロンプト＆半自動運用ガイド】")
    ai_prompt = """あなたはAI画像・SNS映像審査専用の評価AIです。

【評価ルール】
- 画像は“1枚ごとに完全独立”で採点してください。他の画像との比較・順位づけ・相対評価・連動配点は禁止です。
- 評価軸は4つ（各100点満点）。各項目の意味・観点は下記通りで、重複や曖昧な採点は不可です。
- Reason欄には各軸の得点理由・点差の根拠・強みや特徴を必ず具体的に記述してください（重複や抽象的なコメントは禁止）。
- 【重要】CSVには「FileName」列を必ず追加し、評価対象画像のファイル名（例：No3.png）を記載してください。

【評価軸説明】
1. 総合スコア（TotalScore）…静止画・映像化・技術・唯一性・世界観・物語性など、全体完成度を総合的に採点
2. BuzzScore（バズ期待値）…SNS・タイムライン・サムネイルでのバズ力・拡散力
3. StillScore（静止画スコア）…一枚絵としての美しさ・構図・色彩・芸術性・唯一性
4. VideoScore（映像適性スコア）…SORAやMV化した際の映え度・動きやすさ・映像向きか

【出力フォーマット】
No,FileName,TotalScore,BuzzScore,StillScore,VideoScore,Reason

【運用ガイド】
1. 上記プロンプトをAIチャット（ChatGPT/Claude等）に必ずコピペして貼り付けてください。
2. AIが「画像をアップロードしてください」と返すのを必ず確認。
3. その後、NoリネームZIP画像やファイル名順画像をAIにまとめて送信してください。
4. AIが評価（CSV形式テキスト）を返した時点では“ファイルとしては出力されません”。
5. 評価テキストが出力されたら、「この内容をCSVファイルとして出力してください」とAIに依頼してください。
6. AIがCSVファイルを生成したら、そのファイルをダウンロードしてください。
7. 下の「評価済みCSVアップロード」へ流し込めばOKです。

【注意】
- ChatGPTなど多くのAIチャットでは、評価結果はまずテキストで出力されます。
- CSVファイル形式でのダウンロードが必要な場合は、“CSVファイルで出力してください”とAIに依頼する必要があります。
- 必ず「FileName」列でファイル名と評価が正確に紐付くよう運用してください。
"""
    st.code(ai_prompt, language="markdown")
    st.markdown("""
    **【半自動運用手順：現実のAI評価フロー】**  
    1. 上記プロンプトをAIチャットに貼り付け→「画像をください」確認  
    2. NoリネームZIP画像やファイル名順画像をそのまま投げる  
    3. AIがCSV形式の評価テキストを返す  
    4. AIに「この内容をCSVファイルで出力してください」と依頼（必須）  
    5. CSVファイルをダウンロード  
    6. この画面で「評価済みCSVアップロード」→ZIP/サムネ一覧連携  
    """)

    # --- 評価済みCSVアップロード＆ZIP化（FileNameマッチング対応） ---
    st.markdown("---")
    st.subheader("評価済みCSVアップロード（ファイル名マッチ＋高画質サムネ/拡大）")
    eval_up = st.file_uploader("評価済みCSVをアップ", type="csv", key="evalcsvbottom")
    if eval_up:
        df_eval = pd.read_csv(eval_up)
        # ファイル名→評価マップ
        eval_map = {str(row['FileName']): row for _, row in df_eval.iterrows()}
        st.markdown("---")
        st.subheader("【評価反映サムネ一覧（ファイル名マッチ・高画質/拡大ボタン付）】")
        cols = st.columns(NUM_COLS)
        for idx, file in enumerate(uploaded_files):
            img = Image.open(file)
            fname = os.path.basename(file.name)
            with cols[idx % NUM_COLS]:
                st.image(img, caption=f"{fname}", width=400)
                if eval_map.get(fname) is not None:
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

        # --- 拡大サムネ：閉じるボタンで確実に消えるバグ修正版 ---
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
                    fname = os.path.basename(file.name)
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
                    img_name = f"{total}_{buzz}_{still}_{video}_{clean(reason)}.png"
                    save_path = os.path.join(tmpdir, img_name)
                    img.save(save_path)
                    zipf.write(save_path, arcname=img_name)
            with open(zip_path, "rb") as f:
                st.download_button("スコア＋コメント名ZIPダウンロード", f, file_name="Eval_named_images.zip")
else:
    st.info("画像をアップロードしてください。")
