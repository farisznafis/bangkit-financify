import pandas as pd

def show_data(file_path1, file_path2, file_path3):
    df = pd.read_csv(file_path1)
    df2 = pd.read_csv(file_path2)
    df3 = pd.read_csv(file_path3)

    print(df)
    print(df2)
    print(df3)

def preprocess_data(file_path1, output_file_path):
    # Membaca file CSV pertama
    df = pd.read_csv(file_path1)

    # Melelehkan kolom bulan-tahun menjadi dua kolom terpisah
    df_melted = pd.melt(df, id_vars=['City'], var_name='Month_Year', value_name='CPI')

    # Memisahkan kolom "Month_Year" menjadi dua kolom terpisah
    df_melted[['Month', 'Year']] = df_melted['Month_Year'].str.split('_', expand=True)

    # Menampilkan kolom "Kota," "Month," "Year," dan "Inflation"
    df_result = df_melted.loc[:, ['City', 'Month', 'Year', 'CPI']]

    # Menyimpan DataFrame ke dalam file CSV
    df_result.to_csv(output_file_path, index=False)

    print("Preprocessing completed. Result saved to:", output_file_path)

def merge_datasets(path_inflation, path_cpi, output_path):
    # Membaca dataset Inflation dari file CSV
    df_inflation = pd.read_csv(path_inflation)

    # Membaca dataset CPI dari file CSV
    df_cpi = pd.read_csv(path_cpi)

    # Menggabungkan kedua dataset berdasarkan kolom 'City', 'Month', dan 'Year'
    df_combined = pd.merge(df_inflation, df_cpi, on=['City', 'Month', 'Year'])

    # Menyimpan hasil penggabungan ke file CSV
    df_combined.to_csv(output_path, index=False)

    print("Dataset merging completed. Result saved to:", output_path)
    return df_combined

def show_nan_rows(file_path):
    # Baca dataset
    df = pd.read_csv(file_path)

    # Cari baris dengan nilai NaN
    nan_rows = df[df.isnull().any(axis=1)]

    # Tampilkan baris yang mengandung nilai NaN
    print("Rows with NaN values:")
    print(nan_rows)

# # Contoh penggunaan fungsi pertama
# file_path1 = './Dataset/inflasicpi.csv'
# output_file_path = './Dataset/inflasicpifix.csv'
# preprocess_data(file_path1, output_file_path)

# # Contoh penggunaan fungsi kedua
# path_inflation = './Dataset/inflasibulanfix_v2.csv'
# path_cpi = './Dataset/inflasicpifix.csv'
# output_path = './Dataset/inflasi_v3.csv'
# merge_datasets(path_inflation, path_cpi, output_path)

file_path1 = './Dataset/inflasicpifix.csv'
file_path2 = './Dataset/inflasibulanfix_v2.csv'
file_path3 = './Dataset/inflasi_v3.csv'
show_data(file_path1, file_path2, file_path3)

# # Contoh penggunaan fungsi ketiga
# file_path = './Dataset/inflasi_v3.csv'
# show_nan_rows(file_path)
