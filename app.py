import streamlit as st
from PIL import Image
import pandas as pd
from fpdf import FPDF
import tempfile
import os
import base64

st.set_page_config(layout="wide")
st.title("画像評価AIサムネ比較システム")

st.markdown("""
⬇️ 評価サイクル 4ステップ
1. 画像をまとめてアップロード
2. PDFを自動生成＆ダウンロード
3. AIに新規チャットにてPDFファイルをそのまま渡し評価させる（CSV/テキスト出力まで自動）
4. 評価CSVをアップロード → サムネ下にコメント/総合スコアが表示。サムネクリックで原寸DLもOK

※ファイル名や評価コメントに日本語を使ってもOK！PDFはNoだけでエラーなし。
""")

uploaded_files = st.file_uploader(
    "画像をまとめてアップロード",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)
image_data = []
orig_images = []

# モーダル制御
if 'modal_idx' not in st.session_state:
    st.session_state['modal_idx'] = None

def open_modal(idx):
    st.session_state['modal_idx'] = idx

def close_modal():
    st.session_state['modal_idx'] = None

if uploaded_files:
    st.markdown("---")
    st.subheader("PDF自動生成＆ダウンロード")
    if st.button("PDF作成＆ダウンロード（Noのみ表示・エラーゼロ保証）"):
        with tempfile.TemporaryDirectory() as tmpdir:
            images = [Image.open(f) for f in uploaded_files]
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()
            pdf.set_font("Arial", size=14)
            prompt_text = """INSTRUCTIONS FOR AI EVALUATION
- Evaluate each image independently by its number (No). Do NOT compare with other images.
- For each image, output these columns in CSV: No, BuzzScore, StillScore, VideoScore, Reason, TotalScore
- BuzzScore: your integrated rating for viral potential (high/medium/low).
- StillScore: 1–10 points (static visual quality).
- VideoScore: 1–5 stars (video/animation potential).
- Reason: short comment in Japanese about your evaluation.
- TotalScore: ([BuzzScore: high=10/medium=7/low=3] + StillScore + [VideoScore: 1★=2, 2★=4, 3★=6, 4★=8, 5★=10]) / 3 (rounded to 1 decimal).
- Output as CSV. After output, upload the CSV file to this app.
"""
            pdf.multi_cell(0, 10, prompt_text)
            pdf.set_font("Arial", size=11)
            cell_w = (297 - 30) / 2
            cell_h = (210 - 30) / 2
            margin_x, margin_y = 15, 15

            for page_start in range(0, len(images), 4):
                pdf.add_page()
                for pos_in_page in range(4):
                    idx = page_start + pos_in_page
                    if idx >= len(images):
                        break
                    col = pos_in_page % 2
                    row = pos_in_page // 2
                    x = margin_x + cell_w * col
                    y = margin_y + cell_h * row

                    img = images[idx]
                    tmp_img_path = os.path.join(tmpdir, f"img_{idx}.png")
                    img_h = cell_h - 25
                    w0, h0 = img.size
                    img_w = int(img_h * w0 / h0)
                    img_big = img.copy()
                    img_big = img_big.resize((img_w * 3, int(img_h * 3)))
                    img_big.save(tmp_img_path, format="PNG")
                    pdf.image(tmp_img_path, x=x+5, y=y+5, h=img_h)
                    pdf.set_xy(x+5, y+5+img_h+2)
                    pdf.set_font("Arial", size=11)
                    pdf.cell(cell_w - 10, 7, f"No.{idx+1}", ln=1)

            pdf_output = os.path.join(tmpdir, "image_grid.pdf")
            pdf.output(pdf_output)
            with open(pdf_output, "rb") as f:
                st.download_button("PDFダウンロード（Noのみ表示）", f, file_name="image_grid.pdf", mime="application/pdf")

    st.markdown("---")
    st.subheader("AI評価CSVアップロード（No, BuzzScore, StillScore, VideoScore, Reason, TotalScore）")
    st.markdown("・CSVは必ず「No, BuzzScore, StillScore, VideoScore, Reason, TotalScore」列順で作成してください。")
    eval_file = st.file_uploader("評価結果CSVをアップロード", type='csv', key='eval')
    eval_map = {}
    if eval_file:
        eval_df = pd.read_csv(eval_file)
        merged = pd.DataFrame({'No': [i+1 for i in range(len(uploaded_files))]})
        merged = pd.merge(merged, eval_df, on='No', how='left')
        eval_map = merged.set_index("No").to_dict("index")
        st.markdown('<a id="grid_anchor"></a>', unsafe_allow_html=True)
        st.success("評価ファイルアップロード完了！下にサムネ評価一覧が表示されます。")

    st.markdown("---")
    st.subheader("サムネ比較一覧（4カラム）｜サムネクリックで原寸プレビュー")
    cols = st.columns(4)
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        buffered = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        image.save(buffered, format="PNG")
        buffered.close()
        with open(buffered.name, "rb") as img_file:
            b64_img = base64.b64encode(img_file.read()).decode()
        with cols[idx % 4]:
            st.image(image, caption=f"No.{idx+1}", width=220)
            # サムネクリックでモーダル
            btn_label = f"原寸プレビュー"
            if st.button(btn_label, key=f"modal_btn_{idx}"):
                open_modal(idx)
            eval_info = eval_map.get(idx+1)
            if eval_info and pd.notna(eval_info.get('BuzzScore')):
                st.markdown(
                    f"""<div style="font-size: 13px; background:#222; border-radius:6px; color:#e4e4ff; padding:3px 8px 2px 8px; margin-top:-8px; margin-bottom:10px;">
                    <b>バズ期待値:</b> {eval_info['BuzzScore']}　
                    <b>静止画:</b> {eval_info['StillScore']}　
                    <b>映像適性:</b> {eval_info['VideoScore']}<br>
                    <b>総合スコア:</b> {eval_info['TotalScore']}<br>
                    <b>理由:</b> {eval_info['Reason']}
                    </div>""",
                    unsafe_allow_html=True
                )
            else:
                st.markdown('<div style="height:34px"></div>', unsafe_allow_html=True)

    # モーダル原寸プレビュー
    if st.session_state['modal_idx'] is not None:
        idx = st.session_state['modal_idx']
        image = Image.open(uploaded_files[idx])
        with st.container():
            st.markdown(
                """
                <style>
                .modal-bg {position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.88);z-index:1000;display:flex;align-items:center;justify-content:center;}
                .modal-img {border-radius:10px;box-shadow:0 0 20px #000;}
                .modal-close {position:absolute;top:2vw;right:4vw;font-size:2.5rem;color:#fff;cursor:pointer;}
                </style>
                """, unsafe_allow_html=True)
            st.markdown('<div class="modal-bg" onclick="window.location.reload();">', unsafe_allow_html=True)
            st.image(image, use_column_width=True, caption=f"No.{idx+1} 原寸")
            st.markdown(
                '<div class="modal-close" onclick="window.location.reload();">&times;</div></div>',
                unsafe_allow_html=True
            )
        # セッション制御で閉じる
        if st.button("モーダルを閉じる"):
            close_modal()
