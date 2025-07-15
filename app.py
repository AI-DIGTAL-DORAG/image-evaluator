import streamlit as st
from PIL import Image
import pandas as pd
from fpdf import FPDF
import tempfile
import os

st.title("Image Evaluator – グリッドサムネ＆PDF出力")

uploaded_files = st.file_uploader("画像をまとめてアップロード", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
image_data = []

if uploaded_files:
    st.subheader("画像サムネ一覧（4列グリッド表示）")
    cols = st.columns(4)
    images = []
    filenames = []
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        images.append(image)
        filenames.append(file.name)
        with cols[idx % 4]:
            st.image(image, caption=f"No.{idx+1}: {file.name}", width=320)
        image_data.append({'No': idx+1, 'FileName': file.name})
    
    df_images = pd.DataFrame(image_data)
    csv_data = df_images.to_csv(index=False).encode('utf-8')
    st.download_button("画像リストCSVをダウンロード", csv_data, file_name="images_list.csv", mime='text/csv')

    # PDF自動生成機能
    if st.button("サムネ一覧PDFを自動生成"):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()
            cell_w, cell_h = 60, 55  # サムネ1枚のスペース
            margin_x, margin_y = 12, 15
            n_cols = 4
            x, y = margin_x, margin_y

            for idx, img in enumerate(images):
                # 画像を一時保存してリサイズ
                tmp_img_path = os.path.join(tmpdir, f"img_{idx}.jpg")
                img.thumbnail((cell_w-2, cell_h-10))
                img.save(tmp_img_path)
                pdf.image(tmp_img_path, x=x+1, y=y+3, w=cell_w-2)
                # ファイル名キャプション
                caption = f"No.{idx+1}: {filenames[idx][:26]}"
                pdf.set_xy(x, y+cell_h-6)
                pdf.set_font("Arial", size=8)
                pdf.multi_cell(cell_w-2, 4, caption, align='L')
                # 次のグリッド座標
                x += cell_w
                if (idx+1) % n_cols == 0:
                    x = margin_x
                    y += cell_h
                    if y + cell_h > 200:  # ページ下部まで来たら改ページ
                        pdf.add_page()
                        y = margin_y
            # PDF保存
            pdf_output = os.path.join(tmpdir, "image_grid.pdf")
            pdf.output(pdf_output)
            with open(pdf_output, "rb") as f:
                st.download_button("PDFダウンロード", f, file_name="image_grid.pdf", mime="application/pdf")
else:
    df_images = None

# 評価CSVアップロード部分は前回のまま
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
