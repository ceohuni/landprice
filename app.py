#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import geopandas as gpd
import pandas as pd
import zipfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from datetime import datetime

def search_in_zip(zip_file_paths, search_csv_path, search_column, output_columns, output_filename, progress_bar, progress_label):
    filtered_all = gpd.GeoDataFrame()
    crs = None  # 좌표계 저장용

    try:
        # CSV 파일을 cp949로 읽음
        search_df = pd.read_csv(search_csv_path, encoding='cp949')  
        search_values = search_df[search_column].astype(str).tolist()
    except Exception as e:
        messagebox.showerror("오류", f"CSV 파일을 불러오는 중 오류 발생: {e}")
        return

    # --- 저장 경로 설정: 선택한 CSV 파일과 동일한 위치에 생성 ---
    csv_directory = os.path.dirname(os.path.abspath(search_csv_path))
    result_folder = os.path.join(csv_directory, output_filename)
    # -------------------------------------------------------

    total_shp_files = sum(
        1
        for zip_file_path in zip_file_paths
        for file_name in zipfile.ZipFile(zip_file_path).namelist()
        if file_name.endswith('.shp')
    )

    if total_shp_files == 0:
        messagebox.showwarning("주의", "선택한 ZIP 파일 내에 .shp 파일이 없습니다.")
        return

    progress_bar['maximum'] = total_shp_files
    current_progress = 0

    for zip_file_path in zip_file_paths:
        with zipfile.ZipFile(zip_file_path, 'r') as z:
            file_list = z.namelist()

            for file_name in file_list:
                if file_name.endswith('.shp'):
                    try:
                        gdf = gpd.read_file(f"zip://{zip_file_path}!{file_name}", encoding="cp949")

                        if 'A0' in gdf.columns:
                            filtered = gdf[gdf['A0'].astype(str).isin(search_values)]
                            if not filtered.empty:
                                filtered = filtered.copy()
                                # ✅ 구역 여부 체크 컬럼 추가 로직
                                filtered.loc[:, '도시지역'] = filtered['A7'].apply(lambda x: 'O' if 'UQA001' in str(x) else '')
                                filtered.loc[:, '관리지역'] = filtered['A7'].apply(lambda x: 'O' if 'UQB001' in str(x) else '')
                                filtered.loc[:, '농림지역'] = filtered['A7'].apply(lambda x: 'O' if 'UQC001' in str(x) else '')
                                filtered.loc[:, '자연환경보전지역'] = filtered['A7'].apply(lambda x: 'O' if 'UQD001' in str(x) else '')
                                filtered.loc[:, '주거지역'] = filtered['A7'].apply(lambda x: 'O' if 'UQA100' in str(x) else '')
                                filtered.loc[:, '상업지역'] = filtered['A7'].apply(lambda x: 'O' if 'UQA200' in str(x) else '')
                                filtered.loc[:, '공업지역'] = filtered['A7'].apply(lambda x: 'O' if 'UQA300' in str(x) else '')
                                filtered.loc[:, '녹지지역'] = filtered['A7'].apply(lambda x: 'O' if 'UQA400' in str(x) else '')
                                filtered.loc[:, '보전관리지역'] = filtered['A7'].apply(lambda x: 'O' if 'UQB300' in str(x) else '')
                                filtered.loc[:, '생산관리지역'] = filtered['A7'].apply(lambda x: 'O' if 'UQB200' in str(x) else '')
                                filtered.loc[:, '계획관리지역'] = filtered['A7'].apply(lambda x: 'O' if 'UQB100' in str(x) else '')
                                filtered.loc[:, '홍수관리구역'] = filtered['A7'].apply(lambda x: 'O' if 'UJB400' in str(x) else '')
                                filtered.loc[:, '하천구역'] = filtered['A7'].apply(lambda x: 'O' if 'UJB100' in str(x) else '')
                                filtered.loc[:, '농업진흥지역'] = filtered['A7'].apply(lambda x: 'O' if 'UEA100' in str(x) else '')
                                filtered.loc[:, '농업진흥구역'] = filtered['A7'].apply(lambda x: 'O' if 'UEA110' in str(x) else '')
                                filtered.loc[:, '농업보호구역'] = filtered['A7'].apply(lambda x: 'O' if 'UEA120' in str(x) else '')

                                extended_columns = output_columns + [
                                    '도시지역', '관리지역', '농림지역', '자연환경보전지역', '주거지역', '상업지역', '공업지역', '녹지지역', '보전관리지역', '생산관리지역', '계획관리지역', '홍수관리구역', '하천구역', '농업진흥지역', '농업진흥구역', '농업보호구역', 'geometry'
                                ]
                                # 존재하지 않는 컬럼은 제외하고 선택
                                actual_columns = [c for c in extended_columns if c in filtered.columns]
                                filtered = filtered[actual_columns]

                                if not crs:
                                    crs = gdf.crs

                                filtered_all = pd.concat([filtered_all, filtered], ignore_index=True)

                    except Exception as e:
                        print(f"파일 {file_name} 읽기 오류: {e}")

                    current_progress += 1
                    progress_bar['value'] = current_progress
                    progress_label.config(text=f"진행률: {current_progress / total_shp_files * 100:.2f}%")
                    root.update_idletasks()

    if not filtered_all.empty:
        # 결과 폴더 생성
        os.makedirs(result_folder, exist_ok=True)

        # 1. CSV 저장 (geometry 제외)
        csv_path = os.path.join(result_folder, f"{output_filename}.csv")
        filtered_all.drop(columns="geometry").to_csv(csv_path, index=False, encoding="utf-8-sig")

        # 2. SHP 저장을 위한 문자열 정제 (cp949 호환)
        def safe_str(val):
            try:
                return str(val).encode('cp949', errors='ignore').decode('cp949')
            except:
                return ''

        for col in filtered_all.columns:
            if filtered_all[col].dtype == object:
                filtered_all[col] = filtered_all[col].map(safe_str)

        # 3. SHP 저장
        shp_path = os.path.join(result_folder, f"{output_filename}.shp")
        final_gdf = gpd.GeoDataFrame(filtered_all, geometry='geometry', crs=crs)
        final_gdf.to_file(shp_path, driver="ESRI Shapefile", encoding="cp949")

        show_info_message("완료", f"검색 결과가 폴더에 저장되었습니다:\n{result_folder}")
    else:
        show_info_message("결과 없음", "검색된 결과가 없습니다.")

    progress_bar['value'] = 0
    progress_label.config(text="진행률: 0%")

# --- GUI 관련 함수 ---

def select_zip_files():
    file_paths = filedialog.askopenfilenames(filetypes=[("ZIP files", "*.zip")])
    if file_paths:
        zip_file_entry.delete(0, tk.END)
        zip_file_entry.insert(0, ','.join(file_paths))

def select_csv_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        csv_file_entry.delete(0, tk.END)
        csv_file_entry.insert(0, file_path)

def on_search():
    zip_input = zip_file_entry.get()
    search_csv_path = csv_file_entry.get()
    search_column = column_entry.get()
    output_columns_raw = output_columns_entry.get()
    output_filename = file_name_entry.get()

    if not zip_input or not search_csv_path or not search_column or not output_columns_raw or not output_filename:
        messagebox.showerror("오류", "모든 입력 값을 채워주세요.")
        return

    zip_files = zip_input.split(',')
    output_columns = [c.strip() for c in output_columns_raw.split(',')]

    search_thread = threading.Thread(
        target=search_in_zip,
        args=(zip_files, search_csv_path, search_column, output_columns, output_filename, progress_bar, progress_label)
    )
    search_thread.start()

def show_info_message(title, message):
    root.after(0, lambda: messagebox.showinfo(title, message))

# --- 메인 윈도우 설정 ---

root = tk.Tk()
root.title("ZIP 내 Shapefile 검색기 (CSV 폴더 저장형)")
root.geometry("600x400")

# 레이아웃 구성
tk.Label(root, text="1. 대상 ZIP 파일들").grid(row=0, column=0, sticky="w", padx=10, pady=5)
zip_file_entry = tk.Entry(root, width=50)
zip_file_entry.grid(row=0, column=1, pady=5)
tk.Button(root, text="파일 선택", command=select_zip_files).grid(row=0, column=2, padx=5)

tk.Label(root, text="2. 검색 기준 CSV").grid(row=1, column=0, sticky="w", padx=10, pady=5)
csv_file_entry = tk.Entry(root, width=50)
csv_file_entry.grid(row=1, column=1, pady=5)
tk.Button(root, text="파일 선택", command=select_csv_file).grid(row=1, column=2, padx=5)

tk.Label(root, text="3. CSV 내 검색 컬럼").grid(row=2, column=0, sticky="w", padx=10, pady=5)
column_entry = tk.Entry(root, width=50)
column_entry.grid(row=2, column=1, pady=5)
column_entry.insert(0, 'PNU')

tk.Label(root, text="4. 출력할 원본 컬럼").grid(row=3, column=0, sticky="w", padx=10, pady=5)
output_columns_entry = tk.Entry(root, width=50)
output_columns_entry.grid(row=3, column=1, pady=5)
output_columns_entry.insert(0, 'A0,A2,A6,A7,A8,A9,A10')

today_str = datetime.today().strftime("%y%m%d")
tk.Label(root, text="5. 결과 폴더/파일 이름").grid(row=4, column=0, sticky="w", padx=10, pady=5)
file_name_entry = tk.Entry(root, width=50)
file_name_entry.grid(row=4, column=1, pady=5)
file_name_entry.insert(0, f"{today_str}_토지이용계획_결과")

tk.Button(root, text="검색 시작", command=on_search, bg="#e1e1e1", height=2).grid(row=5, column=1, pady=20)

progress_bar = ttk.Progressbar(root, orient='horizontal', mode='determinate', length=350)
progress_bar.grid(row=6, column=1, pady=5)

progress_label = tk.Label(root, text="진행률: 0%")
progress_label.grid(row=7, column=1)

root.mainloop()


# In[ ]:




