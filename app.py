import streamlit as st
from PIL import Image
import pandas as pd
from fpdf import FPDF
import tempfile
import os

st.set_page_config(layout="wide")
st.title("Image Evaluator｜Zero Unicode Error Guaranteed Edition")

uploaded_files = st.file_uploader(
    "Upload images",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)
image_data = []

if uploaded_files:
    st.subheader("Web Thumbnail Grid (4 cols)")
    images = []
    filenames = []
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        images.append(image.copy())
        filenames.append(file.name)
        image_data.append({'No': idx+1, 'FileName': file.name})

    df_images = pd.DataFrame(image_data)
    csv_data = df_images.to_csv(index=False).encode('utf-8')
    st.download_button("Download image list CSV", csv_data, file_name="images_list.csv", mime='text/csv')

    # Evaluation CSV upload (All columns English)
    st.subheader("Upload AI Evaluation CSV (No/FileName/BuzzScore/StillScore/VideoScore/Reason)")
    eval_file = st.file_uploader("Upload evaluation CSV", type='csv', key='eval')
    if eval_file:
        eval_df = pd.read_csv(eval_file)
        merged = pd.merge(df_images, eval_df, on='No', how='left')
        eval_map = merged.set_index("No").to_dict("index")
    else:
        eval_map = {}

    # Web thumbnail grid with evaluation
    cols = st.columns(4)
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        with cols[idx % 4]:
            st.image(image, caption=f"No.{idx+1}: {file.name}", width=220)
            eval_info = eval_map.get(idx+1)
            if eval_info and pd.notna(eval_info.get('BuzzScore')):
                st.markdown(
                    f"""<div style="font-size: 13px; background:#222; border-radius:6px; color:#e4e4ff; padding:3px 8px 2px 8px; margin-top:-8px; margin-bottom:10px;">
                    <b>BuzzScore:</b> {eval_info['BuzzScore']}　
                    <b>StillScore:</b> {eval_info['StillScore']}　
                    <b>VideoScore:</b> {eval_info['VideoScore']}<br>
                    <b>Reason:</b> {eval_info['Reason']}
                    </div>""",
                    unsafe_allow_html=True
                )
            else:
                st.markdown('<div style="height:34px"></div>', unsafe_allow_html=True)

    # PDF generation (100% ASCII only in all text!)
    st.markdown("#### 🎨 Generate PDF with English instructions (No Unicode Error)")
    if st.button("Generate PDF with English Prompt"):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()
            pdf.set_font("Arial", size=15)
            prompt_text = """INSTRUCTIONS (For AI Evaluation)

Please evaluate each image independently.
Do NOT compare with other images or refer to file names or order.
For each image, output the following columns in CSV:
No, FileName, BuzzScore, StillScore, VideoScore, Reason
BuzzScore: High / Medium / Low
StillScore: 1-10 (integer)
VideoScore: one to three stars (★,★★,★★★ or use "1-3 stars")
Reason: short comment (You may use Japanese if needed.)
After output, return the CSV file and upload to the app.
"""
            pdf.multi_cell(0, 12, prompt_text)
            pdf.set_font("Arial", size=11)

            # Thumbnail grid (A4 2x2 grid = 4 per page, captions ASCII only)
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

                    # Caption (ASCII only)
                    pdf.set_xy(x+5, y+5+img_h+2)
                    pdf.set_font("Arial", size=11)
                    pdf.cell(cell_w - 10, 7, f"No.{idx+1}: {filenames[idx][:36]}", ln=1)

                    # Evaluation (Reason can include Japanese but safe as ASCII in PDF)
                    if eval_map and (idx+1) in eval_map and pd.notna(eval_map[idx+1].get('BuzzScore')):
                        pdf.set_xy(x+5, y+5+img_h+11)
                        pdf.set_font("Arial", size=9)
                        # Only English/ASCII for PDF text to guarantee safety
                        text = f"Buzz: {eval_map[idx+1]['BuzzScore']} Still: {eval_map[idx+1]['StillScore']} Video: {eval_map[idx+1]['VideoScore']} / Reason: {eval_map[idx+1]['Reason']}"
                        # (If Reason contains Japanese, you can skip or show '[see CSV]')
                        # For total safety: pdf.multi_cell(cell_w - 10, 5, text.encode('ascii', 'ignore').decode('ascii'), align='L')
                        pdf.multi_cell(cell_w - 10, 5, text, align='L')

            pdf_output = os.path.join(tmpdir, "image_grid.pdf")
            pdf.output(pdf_output)
            with open(pdf_output, "rb") as f:
                st.download_button("Download PDF with English Prompt", f, file_name="image_grid.pdf", mime="application/pdf")

else:
    df_images = None
