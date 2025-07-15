import streamlit as st
from PIL import Image
import pandas as pd
from fpdf import FPDF
import tempfile
import os
import base64

st.set_page_config(layout="wide")
st.title("画像評価AIサムネ比較システム｜完全バージョン")

st.markdown("""
### ⬇️ 評価サイクル 4ステップ
1. **画像をまとめてアップロード**  
2. **PDFを自動生成＆ダウンロード**  
3. **AIに新規チャットにてPDFファイルをそのまま渡し評価させる（CSV/テキスト出力まで自動）**  
4. **評価CSVをアップロード → サムネ下にコメント/総合スコアが表示。サムネクリックで原寸DLもOK**  

※ファイル名や評価コメントに日本語を使ってもOK！PDFはNoだけでエラーなし。
""")

uploaded_files = st.file_uploader(
    "画像をまとめてアップロード",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)
image_data = []
orig_images = []  # 元画像保存

if uploaded_files:
    st.markdown("---")
    st.subheader("サムネ比較一覧（4カラム）｜サムネクリックで原寸DL可")
    images = []
    filenames = []
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        images.append(image.copy())
        orig_images.append(image.copy())
        filenames.append(file.name)
        image_data.append({'No': idx+1, 'FileName': file.name})

    df_images = pd.DataFrame(image_data)
    
    # 評価CSVアップロード
    st.markdown("---")
    st.subheader("AI評価CSVアップロード（No, BuzzScore, StillScore, VideoScore, Reason）")
    st.markdown("・CSVは必ず「No, BuzzScore, StillScore, VideoScore, Reason」列順で作成してください。")
    eval_file = st.file_uploader("評価結果CSVをアップロード", type='csv', key='eval')
    if eval_file:
        eval_df = pd.read_csv(eval_file)
        # 総合スコア自動計算（例：BuzzScore高=10,中=7,低=3、StillScore、VideoScore★=2,★★=6,★★★=10で加重平均）
        def buzz_score_val(x):
            return 10 if str(x).strip() == '高' or str(x).strip().lower() == 'high' else 7 if str(x).strip() == '中' or str(x).strip().lower() == 'medium' else 3
        def video_score_val(x):
            if '★★★' in str(x): return 10
            elif '★★' in str(x): return 6
            elif '★' in str(x): return 2
            else: return 0
        eval_df['総合スコア'] = eval_df.apply(
            lambda row: round((buzz_score_val(row['BuzzScore']) + int(row['StillScore']) + video_score_val(row['VideoScore'])) / 3, 1), axis=1)
        merged = pd.merge(df_images, eval_df, on='No', how='left')
        eval_map = merged.set_index("No").to_dict("index")
    else:
        eval_map = {}

    # サムネ＋評価グリッド（キャプションはNoのみ／サムネクリックで原寸DL可）
    cols = st.columns(4)
    for idx, file in enumerate(uploaded_files):
        image = Image.open(file)
        # 原寸画像DL用base64
        buffered = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        image.save(buffered, format="PNG")
        buffered.close()
        with open(buffered.name, "rb") as img_file:
            b64_img = base64.b64encode(img_file.read()).decode()
        dl_link = f'<a href="data:image/png;base64,{b64_img}" download="No{idx+1}.png">🟢原寸DL</a>'

        with cols[idx % 4]:
            st.image(image, caption=f"No.{idx+1}", width=220)
            st.markdown(dl_link, unsafe_allow_html=True)
            eval_info = eval_map.get(idx+1)
            if eval_info and pd.notna(eval_info.get('BuzzScore')):
                st.markdown(
                    f"""<div style="font-size: 13px; background:#222; border-radius:6px; color:#e4e4ff; padding:3px 8px 2px 8px; margin-top:-8px; margin-bottom:10px;">
                    <b>バズ期待値:</b> {eval_info['BuzzScore']}　
                    <b>静止画:</b> {eval_info['StillScore']}　
                    <b>映像適性:</b> {eval_info['VideoScore']}<br>
                    <b>総合スコア:</b> {eval_info['総合スコア']}<br>
                    <b>理由:</b> {eval_info['Reason']}
                    </div>""",
                    unsafe_allow_html=True
                )
            else:
                st.markdown('<div style="height:34px"></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("⬇️ PDF生成（Noのみのキャプション、評価手順プロンプト付き）")
    st.markdown("""
PDF 1ページ目のプロンプト（英語例）  
> Please evaluate each image by its number (No).  
> For each, output: No, BuzzScore, StillScore, VideoScore, Reason  
> "Reason" can be Japanese in CSV, but is not shown in PDF.  
> Download and use the PDF for evaluation.  
""")
    if st.button("PDFダウンロード（Noのみ表示・エラーゼロ保証）"):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()
            pdf.set_font("Arial", size=15)
            prompt_text = """INSTRUCTIONS FOR AI/HUMAN EVALUATION
Please evaluate each image by its number (No).
Do NOT compare images or use file names.
For each, output:
No, BuzzScore, StillScore, VideoScore, Reason
"Reason" can be Japanese in the CSV, but will not appear in the PDF.
Upload the completed CSV to the app.
"""
            pdf.multi_cell(0, 12, prompt_text)
            pdf.set_font("Arial", size=11)

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
                st.download_button("PDFダウンロード（Noのみ表示・エラーゼロ保証）", f, file_name="image_grid.pdf", mime="application/pdf")
