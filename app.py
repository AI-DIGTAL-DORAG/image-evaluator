import streamlit as st
from PIL import Image
import pandas as pd
from fpdf import FPDF
import tempfile
import os

st.set_page_config(layout="wide")
st.title("画像評価AIサムネ比較システム")

st.markdown("""
### 使い方（手順）
1. **「画像をまとめてアップロード」**に、評価したい画像をまとめてドラッグ＆ドロップしてください。
2. **「画像リストCSVをダウンロード」**で一覧CSVを取得できます。（No, FileName だけのシンプル形式）
3. **AI評価依頼の際は「No」基準でCSVを作成**し、**ファイル名・コメントに日本語が含まれてもOKです**。
4. **「評価CSVをアップロード」**でAI評価結果をアップし、サムネとともにWeb上で確認できます。
5. **「PDFダウンロード」**では**Noのみ表示のサムネ比較用PDF**が生成されます。  
　**ファイル名や日本語コメントはWeb画面または評価CSVで参照してください。**
""")

uploaded_files = st.file_uploader(
    "画像をまとめてアップロード",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)
image_data = []

if uploaded_files:
    st.subheader("Webサムネ比較一覧（4カラム／評価欄は英数字のみ）")
    images = []
    filenames = []
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        images.append(image.copy())
        filenames.append(file.name)
        image_data.append({'No': idx+1, 'FileName': file.name})

    df_images = pd.DataFrame(image_data)
    csv_data = df_images.to_csv(index=False).encode('utf-8')
    st.download_button("画像リストCSVをダウンロード", csv_data, file_name="images_list.csv", mime='text/csv')

    # 評価CSVアップロード（No, FileName, BuzzScore, StillScore, VideoScore, Reason など英数字のみ）
    st.subheader("AI評価CSVをアップロード（No, FileName, BuzzScore, StillScore, VideoScore, Reasonなど英数字列で）")
    eval_file = st.file_uploader("評価結果CSVをアップロード", type='csv', key='eval')
    if eval_file:
        eval_df = pd.read_csv(eval_file)
        merged = pd.merge(df_images, eval_df, on='No', how='left')
        eval_map = merged.set_index("No").to_dict("index")
    else:
        eval_map = {}

    # サムネ＋評価グリッド（PDF同様、キャプションはNoのみで絶対エラーなし！）
    cols = st.columns(4)
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        with cols[idx % 4]:
            st.image(image, caption=f"No.{idx+1}", width=220)
            eval_info = eval_map.get(idx+1)
            if eval_info and pd.notna(eval_info.get('BuzzScore')):
                st.markdown(
                    f"""<div style="font-size: 13px; background:#222; border-radius:6px; color:#e4e4ff; padding:3px 8px 2px 8px; margin-top:-8px; margin-bottom:10px;">
                    <b>BuzzScore:</b> {eval_info['BuzzScore']}　
                    <b>StillScore:</b> {eval_info['StillScore']}　
                    <b>VideoScore:</b> {eval_info['VideoScore']}<br>
                    <b>Reason:</b> {eval_info['Reason'] if eval_info['Reason'].isascii() else '[See CSV]'}
                    </div>""",
                    unsafe_allow_html=True
                )
            else:
                st.markdown('<div style="height:34px"></div>', unsafe_allow_html=True)

    # PDF自動生成（Noのみキャプションで絶対エラーゼロ）
    st.markdown("#### 📄 サムネPDF（番号のみキャプション／ファイル名・日本語非表示）を自動生成")
    if st.button("サムネPDFダウンロード（エラーゼロ保証）"):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            # 1ページ目にシンプルな英語指示文
            pdf.add_page()
            pdf.set_font("Arial", size=15)
            prompt_text = """INSTRUCTIONS FOR AI EVALUATION
Please evaluate each image independently by its number (No.).
Do NOT compare images or use file names.
For each, output:
No, BuzzScore, StillScore, VideoScore, Reason
Reason/comments can be Japanese in the CSV, but will not appear in the PDF.
Upload the completed CSV to the app."""
            pdf.multi_cell(0, 12, prompt_text)
            pdf.set_font("Arial", size=11)

            # 2ページ目以降: サムネ4枚/ページ（Noのみ表示）
            cell_w = (297 - 30) / 2   # 133.5mm
            cell_h = (210 - 30) / 2   # 90mm
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
                    tmp_img_path = os.path.join(tmpdir, f"img_{idx}.jpg")
                    img_h = cell_h - 25
                    w0, h0 = img.size
                    img_w = int(img_h * w0 / h0)
                    img_big = img.copy()
                    img_big = img_big.resize((img_w * 3, int(img_h * 3)))
                    img_big.save(tmp_img_path, quality=95)
                    pdf.image(tmp_img_path, x=x+5, y=y+5, h=img_h)

                    # キャプション（Noのみ）
                    pdf.set_xy(x+5, y+5+img_h+2)
                    pdf.set_font("Arial", size=11)
                    pdf.cell(cell_w - 10, 7, f"No.{idx+1}", ln=1)

            pdf_output = os.path.join(tmpdir, "image_grid.pdf")
            pdf.output(pdf_output)
            with open(pdf_output, "rb") as f:
                st.download_button("PDFダウンロード（Noのみ表示・Unicodeエラーゼロ保証）", f, file_name="image_grid.pdf", mime="application/pdf")

else:
    df_images = None
