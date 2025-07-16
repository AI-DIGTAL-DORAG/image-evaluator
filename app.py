import streamlit as st
from PIL import Image
import pandas as pd
import tempfile
import os
from zipfile import ZipFile

st.set_page_config(layout="wide")
st.title("AI画像評価システム｜Noリネーム＋スコア名ZIP完全版")

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

    # --- ここで初めてプロンプト表示！ ---
    st.markdown("---")
    st.markdown("## 🟣【AI評価プロンプト（コピペ→AIチャットに貼り付け！）】")
    ai_prompt = """あなたはAI画像・SNS映像審査専用の評価AIです。

【評価ルール】
- 画像は“1枚ごとに完全独立”で採点してください。他の画像との比較・順位づけ・相対評価・連動配点は禁止です。
- 評価軸は4つ（各100点満点）。各項目の意味・観点は下記通りで、重複や曖昧な採点は不可です。
- Reason欄には各軸の得点理由・点差の根拠・強みや特徴を必ず具体的に記述してください（重複や抽象的なコメントは禁止）。

【評価軸説明】
1. 総合スコア（TotalScore）…静止画・映像化・技術・唯一性・世界観・物語性など、全体完成度を総合的に採点
2. BuzzScore（バズ期待値）…SNS・タイムライン・サムネイルでのバズ力・拡散力
3. StillScore（静止画スコア）…一枚絵としての美しさ・構図・色彩・芸術性・唯一性
4. VideoScore（映像適性スコア）…SORAやMV化した際の映え度・動きやすさ・映像向きか

【出力フォーマット】
No,TotalScore,BuzzScore,StillScore,VideoScore,Reason

【絶対運用ルール】
- 画像を受信したら、各画像を“完全独立”かつ“厳格”に評価し、上記CSV形式で全件まとめて一括出力してください。
- 評価以外の説明・質問・案内・確認・雑談・処理提案は一切禁止です。
- 画像が受信されていない場合のみ、「画像をアップロードしてください」とだけ返答してください。

【出力例】
No,TotalScore,BuzzScore,StillScore,VideoScore,Reason
1,95,100,93,97,"総合力が非常に高く、特にSNSバズ度が圧倒的。静止画としても引力が強く、MV化しても主役級で動き映える。"
2,89,85,92,90,"静止画の完成度は高いが、バズ期待値はやや控えめ。映像化もしやすい。"
"""
    st.code(ai_prompt, language="markdown")
    st.markdown("""
    **【使い方ガイド】**  
    1. 上記プロンプトをAIチャット（ChatGPT/Claude等）に必ずコピペして貼り付ける  
    2. AIが「画像をアップロードしてください」と返すのを必ず確認  
    3. その後、NoリネームZIP画像をAIにまとめて送信  
    4. AIがCSV形式で評価を返したら下の「評価済みCSVアップロード」で流し込むだけ  
    """)

    # --- 評価済みCSVアップロード＆ZIP化 ---
    st.markdown("---")
    st.subheader("評価済みCSVアップロード（スコア＋コメント付きファイル名ZIP化・高画質サムネ/拡大）")
    eval_up = st.file_uploader("評価済みCSVをアップ", type="csv", key="evalcsvbottom")
    if eval_up:
        df_eval = pd.read_csv(eval_up)
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
