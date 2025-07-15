# --- サムネ4カラム×400pxで表示 ---
NUM_COLS = 4
thumb_width = 400
cols = st.columns(NUM_COLS)
for idx, img in enumerate(images):
    with cols[idx % NUM_COLS]:
        st.image(img, caption=f"No.{idx+1}", width=thumb_width)
        # 原寸DLボタンなどここに
        buf = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(buf, format="PNG")
        buf.close()
        with open(buf.name, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode()
        dl_link = f'<a href="data:image/png;base64,{b64_img}" download="No{idx+1}.png">原寸DL</a>'
        st.markdown(dl_link, unsafe_allow_html=True)
        if st.button("↓拡大", key=f"enlarge_{idx}"):
            enlarge(idx)
