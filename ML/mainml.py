import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Bidirectional, LSTM, Dense

# Baca dataset
file_path = 'inflasibulanfix.csv'
df = pd.read_csv(file_path)

# Pilih kota yang ingin diprediksi
selected_city = 'KOTA YOGYAKARTA'
city_data = df[df['Kota'] == selected_city]

# Pilih kolom inflasi, pendapatan, dan pengeluaran
selected_columns = ['januari_2008', 'februari_2008', 'maret_2008', 'april_2008', 'mei_2008']  # Sesuaikan dengan nama kolom Anda
data = city_data[selected_columns].values

# Normalisasi data
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(data)

# Reshape data untuk LSTM
X_train = scaled_data[:, :-1].reshape((scaled_data.shape[0], 1, scaled_data.shape[1] - 1))
y_train = scaled_data[:, -1]

# Buat model LSTM
model = Sequential()
model.add(Bidirectional(LSTM(50, activation='relu'), input_shape=(X_train.shape[1], X_train.shape[2])))
model.add(Dense(1))
model.compile(optimizer='adam', loss='mse')

# Latih model
model.fit(X_train, y_train, epochs=100)

# Evaluate the model on the training data
mse = model.evaluate(X_train, y_train)
print(f'Mean Squared Error on Training Data: {mse}')


# # Prediksi masa depan
# # Assuming your future data has 4 features and you want to add a placeholder for the missing feature
# future_data = np.array([[0.1, 0.2, 0.3, 0.4]])  # Replace with your actual data
# future_data = np.hstack((future_data, np.zeros((future_data.shape[0], 1))))  # Add a placeholder for the missing feature
# scaled_future_data = scaler.transform(future_data)
# scaled_future_data = scaled_future_data.reshape((1, 1, scaled_future_data.shape[1]))
# predicted_inflation = model.predict(scaled_future_data)
# print(f'Predicted Inflation: {predicted_inflation}')



