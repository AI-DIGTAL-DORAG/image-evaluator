import streamlit as st
from PIL import Image
import pandas as pd
from fpdf import FPDF
import tempfile
import os

st.set_page_config(layout="wide")
st.title("画像サムネ＆日本語AI評価付PDF自動化（闇ポップ毒菓子式）")

uploaded_files = st.file_uploader(
    "画像をまとめてアップロード",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)
image_data = []

# アップした画像リスト化
if uploaded_files:
    st.subheader("Webサムネ比較一覧（4カラム＋日本語評価）")
    images = []
    filenames = []
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        images.append(image.copy())
        filenames.append(file.name)
        image_data.append({'No': idx+1, 'ファイル名': file.name})

    df_images = pd.DataFrame(image_data)
    csv_data = df_images.to_csv(index=False).encode('utf-8')
    st.download_button("画像リストCSVをダウンロード", csv_data, file_name="images_list.csv", mime='text/csv')

    # 評価CSVアップロード（日本語フォーマット！）
    st.subheader("AI日本語評価CSVをアップロード（No/ファイル名/バズ期待値/静止画スコア/映像適性/理由）")
    eval_file = st.file_uploader("評価結果CSVをアップロード", type='csv', key='eval')
    if eval_file:
        eval_df = pd.read_csv(eval_file)
        # "No"でマージ
        merged = pd.merge(df_images, eval_df, on='No', how='left')
        eval_map = merged.set_index("No").to_dict("index")
    else:
        eval_map = {}

    # サムネ＋日本語評価つきWebグリッド表示
    cols = st.columns(4)
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        with cols[idx % 4]:
            st.image(image, caption=f"No.{idx+1}: {file.name}", width=220)
            eval_info = eval_map.get(idx+1)
            if eval_info and pd.notna(eval_info.get('バズ期待値')):
                st.markdown(
                    f"""<div style="font-size: 13px; background:#222; border-radius:6px; color:#ffecf7; padding:3px 8px 2px 8px; margin-top:-8px; margin-bottom:10px;">
                    <b>バズ期待値：</b>{eval_info['バズ期待値']}　
                    <b>静止画：</b>{eval_info['静止画スコア']}　
                    <b>映像適性：</b>{eval_info['映像適性']}<br>
                    <b>理由：</b>{eval_info['理由']}
                    </div>""",
                    unsafe_allow_html=True
                )
            else:
                st.markdown('<div style="height:34px"></div>', unsafe_allow_html=True)

    # PDF自動生成（サムネ＋日本語評価つき！）
    st.markdown("#### 🎨 PDF（高画質サムネ＋日本語評価）を自動生成")
    if st.button("サムネ一覧PDF生成・ダウンロード"):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()
            cell_w, cell_h = 140, 90
            margin_x, margin_y = 15, 15
            n_cols = 2
            x, y = margin_x, margin_y
            page_imgs = 0
            pdf.set_font("Arial", size=11)

            for idx, img in enumerate(images):
                tmp_img_path = os.path.join(tmpdir, f"img_{idx}.jpg")
                img_big = img.copy()
                img_big.thumbnail((cell_w*4, cell_h*4))
                img_big.save(tmp_img_path, quality=95)
                pdf.image(tmp_img_path, x=x+2, y=y+6, w=cell_w-6)
                caption = f"No.{idx+1}: {filenames[idx][:40]}"
                pdf.set_xy(x, y+cell_h-8)
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(cell_w-8, 7, caption, align='L')

                # ↓日本語AI評価（CSVアップされてる場合のみ）
                if eval_map and (idx+1) in eval_map and pd.notna(eval_map[idx+1].get('バズ期待値')):
                    pdf.set_xy(x, y+cell_h-1)
                    pdf.set_font("Arial", size=9)
                    text = f"バズ期待値:{eval_map[idx+1]['バズ期待値']} 静止画:{eval_map[idx+1]['静止画スコア']} 映像適性:{eval_map[idx+1]['映像適性']} / 理由:{eval_map[idx+1]['理由']}"
                    pdf.multi_cell(cell_w-8, 5, text, align='L')

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
                st.download_button("日本語AI評価つきPDFダウンロード", f, file_name="image_grid.pdf", mime="application/pdf")

else:
    df_images = None
