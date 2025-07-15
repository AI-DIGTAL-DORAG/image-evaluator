import streamlit as st
import base64
from PIL import Image
import tempfile
import pandas as pd
from fpdf import FPDF
import os

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

# ----- JS/HTML式サムネクリック原寸モーダルのCSS&JS -----
if uploaded_files:
    st.markdown("""
    <style>
    .modal-bg {position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.92);z-index:10000;display:none;align-items:center;justify-content:center;}
    .modal-bg.show {display:flex;}
    .modal-img {border-radius:10px;box-shadow:0 0 30px #000;max-width:96vw;max-height:96vh;}
    .modal-close {position:absolute;top:2vw;right:4vw;font-size:2.5rem;color:#fff;cursor:pointer;z-index:10002;}
    .modal-label {position:fixed;top:2vw;left:3vw;color:#fff;font-size:2rem;z-index:10002;}
    </style>
    <script>
    function openModal(idx) {
      document.getElementById('modal'+idx).classList.add('show');
    }
    function closeModal(idx) {
      document.getElementById('modal'+idx).classList.remove('show');
    }
    </script>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("PDF自動生成＆ダウンロード")
    if st.button("PDF作成＆ダウンロード（Noのみ表示・エラーゼロ保証）"):
        with tempfile.TemporaryDirectory() as tmpdir:
            images = [Image.open(f) for f in uploaded_files]
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()
            pdf.set_font("Arial", size=14)
            # ★ASCII ONLY! (No unicode, no Japanese, no "★" etc.)
            prompt_text = """INSTRUCTIONS FOR AI EVALUATION
- Evaluate each image independently by its number (No). Do NOT compare with other images.
- For each image, output these columns in CSV: No, BuzzScore, StillScore, VideoScore, Reason, TotalScore
- BuzzScore: your integrated rating for viral potential (high/medium/low).
- StillScore: 1-10 points (static visual quality).
- VideoScore: 1-5 stars (use '1star', '2star', ... '5star', do not use non-ASCII marks).
- Reason: short comment in Japanese about your evaluation. (But Reason is not shown in this PDF.)
- TotalScore: ([BuzzScore: high=10/medium=7/low=3] + StillScore + [VideoScore: 1star=2, 2star=4, 3star=6, 4star=8, 5star=10]) / 3 (rounded to 1 decimal).
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
        st.success("評価ファイルアップロード完了！下にサムネ評価一覧が表示されます。")

    st.markdown("---")
    st.subheader("サムネ比較一覧（4カラム）｜サムネクリックで中央原寸モーダル")

    cols = st.columns(4)
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        buffered = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        image.save(buffered, format="PNG")
        buffered.close()
        with open(buffered.name, "rb") as img_file:
            b64_img = base64.b64encode(img_file.read()).decode()
        modal_id = f"modal{idx}"
        img_tag = f"""
        <a href="javascript:void(0);" onclick="openModal({idx});">
            <img src="data:image/png;base64,{b64_img}" style="width:100%;border-radius:10px;box-shadow:0 0 10px #000;"/>
        </a>
        <div id="{modal_id}" class="modal-bg" onclick="closeModal({idx});">
            <span class="modal-close" onclick="closeModal({idx});event.stopPropagation();">&times;</span>
            <span class="modal-label">No.{idx+1}</span>
            <img src="data:image/png;base64,{b64_img}" class="modal-img"/>
        </div>
        """
        with cols[idx % 4]:
            st.markdown(img_tag, unsafe_allow_html=True)
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
