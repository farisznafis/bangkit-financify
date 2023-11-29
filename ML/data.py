import pandas as pd

# Path ke file CSV pertama
file_path1 = 'inflasibulanfix.csv'

# Membaca file CSV pertama
df = pd.read_csv(file_path1)

# Melelehkan kolom bulan-tahun menjadi dua kolom terpisah
df_melted = pd.melt(df, id_vars=['Kota'], var_name='Month_Year', value_name='Inflation')

# Memisahkan kolom "Month_Year" menjadi dua kolom terpisah
df_melted[['Month', 'Year']] = df_melted['Month_Year'].str.split('_', expand=True)

# Menampilkan kolom "Kota," "Month," "Year," dan "Inflation"
df_result = df_melted.loc[:, ['Kota', 'Month', 'Year', 'Inflation']]

# Mengganti nama kolom 'Kota' menjadi 'City'
df_result = df_result.rename(columns={'Kota': 'City'})

# Menampilkan hasil
print(df_result)


# Menyimpan DataFrame ke dalam file CSV
df_result.to_csv('output.csv', index=False)
