import pandas as pd

# Membaca data inflasi ke dalam DataFrame
file_path = 'inflasibulanfix.csv'
inflasi_df = pd.read_csv(file_path)
inflasi_df.set_index('Kota', inplace=True)

# Mengubah nilai-nilai dalam kolom menjadi numerik
inflasi_df.loc[:, 'januari_2008':'desember_2022'] = inflasi_df.loc[:, 'januari_2008':'desember_2022'].apply(pd.to_numeric, errors='coerce')

# Menghitung tingkat inflasi tahunan
inflasi_df['Avg_Annual_Inflation'] = inflasi_df.loc[:, 'januari_2008':'desember_2022'].mean(axis=1) / 100

# Menampilkan data inflasi
print("Data Inflasi:")
print(inflasi_df[['Avg_Annual_Inflation']])

# Meminta input pengguna untuk tujuan, pendapatan, dan pengeluaran per bulan
tujuan_keuangan = float(input("Masukkan tujuan keuangan Anda: "))
pendapatan_per_bulan = float(input("Masukkan pendapatan per bulan Anda: "))
pengeluaran_per_bulan = float(input("Masukkan pengeluaran per bulan Anda: "))
kota = input("Masukkan kota yang ingin dihitung: ")

# Menghitung lamanya waktu mencapai tujuan dengan inflasi dalam satuan bulan
def calculate_time_to_goal(current_savings, monthly_income, monthly_expense, annual_inflation_rate):
    months = 0
    while current_savings < tujuan_keuangan:
        current_savings += (monthly_income - monthly_expense)
        current_savings *= (1 + annual_inflation_rate / 12)
        months += 1
    return months

# Memperbarui data inflasi di DataFrame
if kota in inflasi_df.index:
    annual_inflation_rate = inflasi_df.loc[kota, 'Avg_Annual_Inflation']
    months_to_goal = calculate_time_to_goal(0, pendapatan_per_bulan, pengeluaran_per_bulan, annual_inflation_rate)
    years_to_goal = months_to_goal // 12
    remaining_months = months_to_goal % 12
    inflasi_df.loc[kota, 'Years_to_Goal'] = years_to_goal
    inflasi_df.loc[kota, 'Months_to_Goal'] = remaining_months
    print("\nHasil Perhitungan:")
    print(inflasi_df.loc[[kota], ['Avg_Annual_Inflation', 'Years_to_Goal', 'Months_to_Goal']])
else:
    print(f"Data untuk kota {kota} tidak ditemukan.")
