# app.py
from flask import Flask, render_template, request
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
import numpy as np

app = Flask(__name__)

# Load the Keras model
model = load_model('all_cities_lstm_model.h5')

# Initialize scaler
scaler = MinMaxScaler()

# Load data
file_path = 'inflasibulanfix.csv'
df = pd.read_csv(file_path)

# Select relevant columns
df = df[['City', 'Month', 'Year', 'Inflation']]

# Remove 'KOTA' from the 'City' column
df['City'] = df['City'].str.replace('KOTA ', '', regex=False)

# Check if 'Inflation' column already contains numeric values
if not pd.api.types.is_numeric_dtype(df['Inflation']):
    # Replace commas with dots in the 'Inflation' column
    df['Inflation'] = df['Inflation'].str.replace(',', '.').astype(float)

# Sort the data
df = df.sort_values(by=['City', 'Year', 'Month'])

# Separate data into time series for each city
city_data = {}
for city in df['City'].unique():
    city_data[city] = df[df['City'] == city]['Inflation'].values

# Combine data for all cities into a single time series
all_cities_data = np.concatenate(list(city_data.values()))

# Function to create time series sequences
def create_time_series(data, time_steps=1):
    X, y = [], []
    for i in range(len(data) - time_steps):
        a = data[i:(i + time_steps)]
        X.append(a)
        y.append(data[i + time_steps])
    return np.array(X), np.array(y)

# Hyperparameters
time_steps = 12
n_features = 1

# Create time series for all cities
X_all, y_all = create_time_series(all_cities_data, time_steps)
X_all = X_all.reshape((X_all.shape[0], X_all.shape[1], n_features))

# Fit the scaler with all inflation data
scaler.fit_transform(all_cities_data.reshape(-1, 1))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    error = None
    prediction = None
    trend = None

    try:
        city = request.form['city']
        historical_inflation = city_data[city]

        input_data = scaler.transform(historical_inflation[-time_steps:].reshape(-1, 1))
        input_data = input_data.reshape((1, time_steps, n_features))

        # Make prediction
        predicted_inflation = model.predict(input_data)

        # Inverse transform the prediction to get the actual value
        predicted_inflation_actual = scaler.inverse_transform(predicted_inflation.reshape(-1, 1))
        prediction = predicted_inflation_actual[0][0]

        # Compare with the most recent actual inflation value
        last_actual_inflation = historical_inflation[-1]

        # Determine the trend
        if prediction > last_actual_inflation:
            trend = 'up'
        elif prediction < last_actual_inflation:
            trend = 'down'
        else:
            trend = 'unchanged'

    except Exception as e:
        error = str(e)

    return render_template('result.html', error=error, prediction=prediction, trend=trend)

if __name__ == '__main__':
    app.run(debug=True)
