import streamlit as st
from PIL import Image
import pandas as pd
from fpdf import FPDF
import tempfile
import os

st.set_page_config(layout="wide")
st.title("画像サムネ＆日本語AI評価PDF完全版（日本語フォント対応）")

uploaded_files = st.file_uploader(
    "画像をまとめてアップロード",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)
image_data = []

def get_jp_font(font_dir):
    font_path = os.path.join(font_dir, "ipaexg.ttf")
    if not os.path.exists(font_path):
        # ダウンロード（Streamlit Cloud可）
        import urllib.request
        url = "https://moji.or.jp/wp-content/ipafont/IPAexfont/ipaexg00401/ipaexg.ttf"
        urllib.request.urlretrieve(url, font_path)
    return font_path

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

    # 評価CSVアップロード
    st.subheader("AI日本語評価CSVをアップロード（No/ファイル名/バズ期待値/静止画スコア/映像適性/理由）")
    eval_file = st.file_uploader("評価結果CSVをアップロード", type='csv', key='eval')
    if eval_file:
        eval_df = pd.read_csv(eval_file)
        merged = pd.merge(df_images, eval_df, on='No', how='left')
        eval_map = merged.set_index("No").to_dict("index")
    else:
        eval_map = {}

    # Webサムネ＋評価つきグリッド表示
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

    # PDF自動生成（1ページ目に評価依頼文→2ページ目以降サムネ4枚/ページ）
    st.markdown("#### 🎨 PDF（日本語フォント＋プロンプト1ページ目付き）を自動生成")
    if st.button("サムネ一覧PDF生成・ダウンロード"):
        with tempfile.TemporaryDirectory() as tmpdir:
            # IPAexGothic日本語フォント準備
            font_path = get_jp_font(tmpdir)

            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_font('IPAGothic', '', font_path, uni=True)

            # 1ページ目：プロンプト・手順
            pdf.add_page()
            pdf.set_font("IPAGothic", size=15)
            prompt_text = """【AI/ChatGPT評価依頼プロンプト】

次の画像リストを「1枚ずつ独立して」評価してください。他の画像や順番、ファイル名の類似を参照しての比較・コメントは一切しないでください。
各画像について「バズ期待値／静止画スコア／映像適性／理由」を日本語で、一枚絵としての魅力のみから記入してください。
評価内容はCSVでまとめて出力してください。
出力後、依頼主にページに戻ってそのファイルを評価アップロード先に入れるよう伝えてください。

（このページの下に画像リストが続きます）
"""
            pdf.multi_cell(0, 12, prompt_text)
            pdf.set_font("IPAGothic", size=11)

            # 2ページ目以降：サムネ＋キャプション＋AI評価
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

                    # 高さ基準で横幅自動計算（アスペクト比維持）
                    img_h = cell_h - 25
                    w0, h0 = img.size
                    img_w = int(img_h * w0 / h0)
                    img_big = img.copy()
                    img_big = img_big.resize((img_w * 3, int(img_h * 3)))
                    img_big.save(tmp_img_path, quality=95)
                    pdf.image(tmp_img_path, x=x+5, y=y+5, h=img_h)

                    # キャプション
                    pdf.set_xy(x+5, y+5+img_h+2)
                    pdf.set_font("IPAGothic", size=11)
                    pdf.cell(cell_w - 10, 7, f"No.{idx+1}: {filenames[idx][:36]}", ln=1)

                    # 日本語AI評価
                    if eval_map and (idx+1) in eval_map and pd.notna(eval_map[idx+1].get('バズ期待値')):
                        pdf.set_xy(x+5, y+5+img_h+11)
                        pdf.set_font("IPAGothic", size=9)
                        text = f"バズ:{eval_map[idx+1]['バズ期待値']} 静止画:{eval_map[idx+1]['静止画スコア']} 映像:{eval_map[idx+1]['映像適性']} / {eval_map[idx+1]['理由']}"
                        pdf.multi_cell(cell_w - 10, 5, text, align='L')

            pdf_output = os.path.join(tmpdir, "image_grid.pdf")
            pdf.output(pdf_output)
            with open(pdf_output, "rb") as f:
                st.download_button("プロンプト付き日本語PDFダウンロード", f, file_name="image_grid.pdf", mime="application/pdf")

else:
    df_images = None
