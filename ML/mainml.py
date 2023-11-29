import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Bidirectional, LSTM, Dense

# Load your dataset
file_path = 'inflasibulanfix.csv'
df = pd.read_csv(file_path)

# Convert string numbers with commas to floats
numeric_columns = df.columns[1:]
df[numeric_columns] = df[numeric_columns].replace(',', '.', regex=True).astype(float)

# Normalize data
scaler = MinMaxScaler()
normalized_data = scaler.fit_transform(df[numeric_columns])

# Prepare the input data
X = normalized_data[:, :-1]
y = normalized_data[:, -1]

# Reshape data for LSTM
X = X.reshape((X.shape[0], 1, X.shape[1]))

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Build the Bidirectional LSTM model
model = Sequential()
model.add(Bidirectional(LSTM(50, activation='relu'), input_shape=(X.shape[1], X.shape[2])))
model.add(Dense(1))
model.compile(optimizer='adam', loss='mse')

# Train the model
model.fit(X_train, y_train, epochs=100, validation_data=(X_test, y_test))

# Evaluate the model on the testing data
mse = model.evaluate(X_test, y_test)
print(f'Mean Squared Error on Testing Data: {mse}')

# # Make predictions on new data (adjust as needed)
# new_data = np.array([[0.1, 0.2, 0.3, 0.4]])  # Replace with your actual data
# new_data = new_data.reshape((new_data.shape[0], 1, new_data.shape[1]))
# scaled_new_data = scaler.transform(new_data)
# predicted_inflation = model.predict(scaled_new_data)
# print(f'Predicted Inflation: {predicted_inflation}')