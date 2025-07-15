import streamlit as st
from PIL import Image
import pandas as pd
import io

st.title("Image Evaluator – サムネ一覧＆AI評価CSVマッチング")

# 1. 画像アップロード
uploaded_files = st.file_uploader("画像をまとめてアップロード", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
image_data = []

if uploaded_files:
    st.subheader("画像サムネ一覧")
    for idx, file in enumerate(uploaded_files, start=1):
        image = Image.open(file)
        st.image(image, caption=f"No.{idx} : {file.name}", width=160)
        image_data.append({'No': idx, 'FileName': file.name})

    df_images = pd.DataFrame(image_data)
    # CSV出力（サムネは含まれないが、ファイル名と番号で管理できる）
    csv_data = df_images.to_csv(index=False).encode('utf-8')
    st.download_button("画像リストCSVをダウンロード", csv_data, file_name="images_list.csv", mime='text/csv')

    st.write("上記一覧画面をスクショor PDF保存 → ChatGPTでAI評価 → 評価CSV（No,Score,Comment等）にして次でアップロード")
else:
    df_images = None

# 2. 評価CSVアップロード＆自動マッチング
st.subheader("AI評価CSVをアップロード（NoやFileNameで紐づけ）")
eval_file = st.file_uploader("評価結果CSVをアップロード", type='csv', key='eval')

if eval_file and df_images is not None:
    eval_df = pd.read_csv(eval_file)
    # 'No' か 'FileName' でマージ。両方あればNo優先
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
        # 評価付きCSV出力
        out_csv = merged.to_csv(index=False).encode('utf-8')
        st.download_button("評価付きCSVをダウンロード", out_csv, file_name="images_with_eval.csv", mime='text/csv')

