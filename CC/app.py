from flask import Flask, render_template, request, jsonify
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
import numpy as np
import os
app = Flask(__name__)

# Mendapatkan path direktori saat ini
current_directory = os.path.dirname(os.path.realpath(__file__))

# Load the pre-trained Keras model
# Load the pre-trained Keras model
model_path = os.path.join(current_directory, 'all_cities_lstm_model_v3.h5')
model = load_model(model_path)

# Initialize scaler
scaler = MinMaxScaler()

# Load data
file_path = './inflasi_v3.csv'
df = pd.read_csv(file_path)

# Select relevant columns
df = df[['City', 'Month', 'Year', 'Inflation', 'CPI']]

# Remove 'KOTA' from the 'City' column
df['City'] = df['City'].str.replace('KOTA ', '', regex=False)

# Check if 'Inflation' and 'CPI' columns already contain numeric values
for col in ['Inflation', 'CPI']:
    if not pd.api.types.is_numeric_dtype(df[col]):
        # Replace commas with dots and convert to float
        df[col] = df[col].str.replace(',', '.').astype(float)

# Sort the data
df = df.sort_values(by=['City', 'Year', 'Month'])

# Scale inflation data and other numerical features
scaler.fit_transform(df[['Inflation', 'CPI']].values)

# Separate data into time series for each city
city_data = {}
for city in df['City'].unique():
    city_data[city] = df[df['City'] == city][['Inflation', 'CPI']].values

# Combine data for all cities into a single time series
all_cities_data = np.concatenate(list(city_data.values()))

# Function to create time series sequences
def create_time_series(data, time_steps=1):
    X, y = [], []
    for i in range(len(data) - time_steps + 1):
        a = data[i:(i + time_steps), :]
        X.append(a)
        y.append(data[i + time_steps - 1, 0])  # Assuming 'Inflation' is in the first column
    return np.array(X), np.array(y)

# Hyperparameters
time_steps = 12
n_features = 2

@app.route('/')
def index():
    return "Hello World!"

@app.route('/predict', methods=['POST'])
def predict():
    error = None
    prediction = None
    trend = None
    time_required = None
    time_required_predicted = None

    try:
        city = request.form['city']
        goal = float(request.form['goal'])
        income = float(request.form['income'])
        expenses = float(request.form['expenses'])
        historical_inflation = city_data[city]

        input_data = scaler.transform(historical_inflation[-time_steps:])
        input_data = input_data.reshape((1, time_steps, n_features))

        # Make prediction
        predicted_inflation = model.predict(input_data)

        # Inverse transform the prediction to get the actual value
        predicted_inflation_actual = scaler.inverse_transform(np.concatenate([predicted_inflation, np.zeros_like(predicted_inflation)], axis=1))
        predicted_inflation_actual = predicted_inflation_actual[:, 0]
        prediction = predicted_inflation_actual[0]

        # Compare with the most recent actual inflation value
        last_actual_inflation = historical_inflation[-1, 0]  # Assuming 'Inflation' is in the first column

        # Determine the trend
        if prediction > last_actual_inflation:
            trend = 'up'
        elif prediction < last_actual_inflation:
            trend = 'down'
        else:
            trend = 'unchanged'

        # Calculate time required based on predicted inflation
        years_to_goal, remaining_months = calculate_time_to_goal(goal, income, expenses, prediction)

        prediction = round(prediction * 100, 2)

    except Exception as e:
        error = str(e)

    return jsonify({
        "prediction": prediction,
        "trend": trend,
        "time_required": {
            "years_to_goal": years_to_goal,
            "remaining_months": remaining_months
        }
    })

def calculate_time_to_goal(goal, income, expenses, savings):
    # Calculate monthly savings
    monthly_savings = income - expenses

    # Calculate the number of months required to reach the goal
    months_to_goal = int((goal - savings) / monthly_savings)

    # Convert months to years and months
    years_to_goal = months_to_goal // 12
    remaining_months = months_to_goal % 12

    return years_to_goal, remaining_months

if  __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
