    # --- 評価反映サムネ＆拡大・一括DL機能 ---
    if df_eval is not None:
        st.markdown("---")
        st.subheader("【評価反映サムネ一覧（2カラム×4行／高画質ソート／拡大付）】")

        # ソート用辞書：ファイル名→idx
        fname2idx = {f"No{idx+1}.png": idx for idx in range(len(uploaded_files))}
        df_eval["TotalScore"] = pd.to_numeric(df_eval["TotalScore"], errors="coerce")
        df_eval_sorted = df_eval.sort_values(by="TotalScore", ascending=False)
        sorted_items = []
        for _, row in df_eval_sorted.iterrows():
            fname = row["FileName"]
            idx = fname2idx.get(fname)
            if idx is not None:
                sorted_items.append((idx, row))

        eval_cols = st.columns(2)
        for i, (img_idx, e) in enumerate(sorted_items):
            col = eval_cols[i % 2]
            with col:
                img = Image.open(uploaded_files[img_idx])
                st.image(img, caption=f"{e['FileName']}", use_container_width=True)
                st.markdown(
                    f"""<div style="font-size: 15px; background:#222; border-radius:8px; color:#e4e4ff; padding:6px 14px 4px 14px; margin-top:10px; margin-bottom:14px;">
                    <b>総合:</b> {e['TotalScore']}　
                    <b>バズ:</b> {e['BuzzScore']}　
                    <b>静止画:</b> {e['StillScore']}　
                    <b>映像:</b> {e['VideoScore']}<br>
                    <b>理由:</b> {e['Reason']}
                    </div>""",
                    unsafe_allow_html=True
                )
                if st.button("拡大", key=f"enlarge_eval_{img_idx}"):
                    enlarge(img_idx)

        # 拡大サムネ（ワンクリックで消す）
        if st.session_state["enlarged_idx"] is not None:
            eidx = st.session_state["enlarged_idx"]
            img_big = Image.open(uploaded_files[eidx])
            st.markdown("---")
            st.markdown(f"### 🟢 高画質最大表示")
            st.image(img_big, use_container_width=True)
            if st.button("拡大を閉じる", key="close_enlarge_eval"):
                clear_enlarge()
                return

        # スコア＋コメント付きファイル名画像を一括ZIP DL
        st.markdown("---")
        st.subheader("4軸スコア＋コメント付きファイル名画像を一括ZIP DL")
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "Eval_named_images.zip")
            from zipfile import ZipFile
            with ZipFile(zip_path, "w") as zipf:
                for idx, file in enumerate(uploaded_files):
                    img = Image.open(file)
                    fname = f"No{idx+1}.png"
                    key = clean_filename(fname)
                    e = df_eval.set_index("FileName").to_dict("index").get(fname, {})
                    total = str(e.get("TotalScore", ""))
                    buzz = str(e.get("BuzzScore", ""))
                    still = str(e.get("StillScore", ""))
                    video = str(e.get("VideoScore", ""))
                    reason = str(e.get("Reason", ""))
                    def clean(s):
                        s = str(s)
                        s = s.replace("/", "／").replace("\\", "＼").replace(":", "：").replace("*", "＊")
                        s = s.replace("?", "？").replace('"', "”").replace("<", "＜").replace(">", "＞").replace("|", "｜")
                        s = s.replace(" ", "_").replace("\n", "")
                        return s[:30]
                    img_name = f"{total}_{buzz}_{still}_{video}_{clean(reason)}.png"
                    save_path = os.path.join(tmpdir, img_name)
                    img.save(save_path)
                    zipf.write(save_path, arcname=img_name)
            with open(zip_path, "rb") as f:
                st.download_button("スコア＋コメント名ZIPダウンロード", f, file_name="Eval_named_images.zip")
