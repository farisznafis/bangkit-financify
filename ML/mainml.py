import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Bidirectional, LSTM, Dense

# Baca data
file_path = 'output.csv'
df = pd.read_csv(file_path)

# Ambil kolom yang relevan
df = df[['City', 'Month', 'Year', 'Inflation']]

# Ganti koma dengan titik pada kolom 'Inflation'
df['Inflation'] = df['Inflation'].str.replace(',', '.').astype(float)

# Urutkan data
df = df.sort_values(by=['City', 'Year', 'Month'])

# Scaling data inflasi
scaler = MinMaxScaler()
df['Inflation'] = scaler.fit_transform(df['Inflation'].values.reshape(-1, 1))

# Pisahkan data menjadi seri waktu untuk setiap kota
city_data = {}
for city in df['City'].unique():
    city_data[city] = df[df['City'] == city]['Inflation'].values

# Fungsi untuk membuat sekuens waktu
def create_time_series(data, time_steps=1):
    X, y = [], []
    for i in range(len(data) - time_steps):
        a = data[i:(i + time_steps)]
        X.append(a)
        y.append(data[i + time_steps])
    return np.array(X), np.array(y)

# Hyperparameter
time_steps = 12  # Sesuaikan dengan panjang sekuens waktu yang ingin Anda gunakan
n_features = 1  # Jumlah fitur (hanya inflasi)

# Membuat dan melatih model LSTM untuk setiap kota
models = {}
for city, data in city_data.items():
    X, y = create_time_series(data, time_steps)
    X = X.reshape((X.shape[0], X.shape[1], n_features))
    
    model = Sequential()
    model.add(Bidirectional(LSTM(50, activation='relu'), input_shape=(time_steps, n_features)))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mse')
    model.fit(X, y, epochs=50, verbose=0)
    
    models[city] = model

# Contoh prediksi untuk suatu kota
sample_city = 'KOTA BANDA ACEH'
input_data = scaler.transform(city_data[sample_city][-time_steps:].reshape(-1, 1))
input_data = input_data.reshape((1, time_steps, n_features))
predicted_inflation = models[sample_city].predict(input_data)

# Inverse transform hasil prediksi untuk mendapatkan nilai sebenarnya
predicted_inflation_actual = scaler.inverse_transform(predicted_inflation.reshape(-1, 1))

print(f'Predicted Inflation for {sample_city}: {predicted_inflation_actual[0][0]}')
