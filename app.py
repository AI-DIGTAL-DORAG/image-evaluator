import streamlit as st
from PIL import Image
import pandas as pd
from fpdf import FPDF
import tempfile
import os

st.set_page_config(layout="wide")
st.title("Image Evaluator｜High-Quality PDF & Quick Web Grid")

uploaded_files = st.file_uploader(
    "画像をまとめてアップロード", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)
image_data = []

if uploaded_files:
    st.subheader("Webサムネ比較一覧（4カラム）")
    cols = st.columns(4)
    images = []
    filenames = []
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        images.append(image.copy())  # PDF用
        filenames.append(file.name)
        with cols[idx % 4]:
            st.image(image, caption=f"No.{idx+1}: {file.name}", width=220)
        image_data.append({'No': idx+1, 'FileName': file.name})

    df_images = pd.DataFrame(image_data)
    csv_data = df_images.to_csv(index=False).encode('utf-8')
    st.download_button("画像リストCSVをダウンロード", csv_data, file_name="images_list.csv", mime='text/csv')

    # PDF自動生成
    st.markdown("#### 🎨 PDF（高画質サムネ＋4枚1ページ）を自動生成")
    if st.button("サムネ一覧PDF生成・ダウンロード"):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()  # 最初のページを先に追加！
            cell_w, cell_h = 140, 85   # 横140×縦85mmで大きめ
            margin_x, margin_y = 15, 15
            n_cols = 2
            x, y = margin_x, margin_y
            page_imgs = 0

            for idx, img in enumerate(images):
                tmp_img_path = os.path.join(tmpdir, f"img_{idx}.jpg")
                img_big = img.copy()
                img_big.thumbnail((cell_w*4, cell_h*4))  # 高画質
                img_big.save(tmp_img_path, quality=95)
                pdf.image(tmp_img_path, x=x+2, y=y+6, w=cell_w-6)
                caption = f"No.{idx+1}: {filenames[idx][:40]}"
                pdf.set_xy(x, y+cell_h-6)
                pdf.set_font("Arial", size=11)
                pdf.multi_cell(cell_w-8, 7, caption, align='L')
                x += cell_w
                page_imgs += 1
                if page_imgs % n_cols == 0:
                    x = margin_x
                    y += cell_h
                if page_imgs % (n_cols*2) == 0 and idx+1 < len(images):
                    pdf.add_page()
                    x, y, page_imgs = margin_x, margin_y, 0
            pdf_output = os.path.join(tmpdir, "image_grid.pdf")
            pdf.output(pdf_output)
            with open(pdf_output, "rb") as f:
                st.download_button("高画質サムネPDFダウンロード", f, file_name="image_grid.pdf", mime="application/pdf")

else:
    df_images = None

# 評価CSVアップロード（AIコメント紐付け）
st.subheader("AI評価CSVをアップロード（NoやFileNameで紐づけ）")
eval_file = st.file_uploader("評価結果CSVをアップロード", type='csv', key='eval')
if eval_file and df_images is not None:
    eval_df = pd.read_csv(eval_file)
    if 'No' in eval_df.columns:
        merged = pd.merge(df_images, eval_df, on='No', how='left')
    elif 'FileName' in eval_df.columns:
        merged = pd.merge(df_images, eval_df, on='FileName', how='left')
    else:
        st.error("評価CSVは 'No' または 'FileName' 列を含めてください。")
        merged = None

    if merged is not None:
        st.subheader("画像とAI評価結果の一覧")
        st.dataframe(merged)
        out_csv = merged.to_csv(index=False).encode('utf-8')
        st.download_button("評価付きCSVをダウンロード", out_csv, file_name="images_with_eval.csv", mime='text/csv')
