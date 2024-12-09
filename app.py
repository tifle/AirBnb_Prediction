import numpy as np
import pandas as pd
import tensorflow as tf
import streamlit as st
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime, timedelta

# Load the saved model
@st.cache_resource
def load_model():
    return tf.keras.models.load_model('LSTM_model.h5')

# Create scalers with caching
@st.cache_resource
def create_scalers():
    # Recreate the scalers with the same configuration as during training
    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    
    # You'll need to provide some sample data to fit the scalers
    # This should match the training data preprocessing
    sample_features = np.random.rand(100, 10)  # 10 features used in training
    sample_target = np.random.rand(100, 1)
    
    scaler_X.fit(sample_features)
    scaler_y.fit(sample_target)
    
    return scaler_X, scaler_y

# Cached model and scalers
model = load_model()
scaler_X, scaler_y = create_scalers()

def generate_feature_engineering(start_date, avg_price, min_nights, max_nights):
    """
    Generate additional features for prediction
    """
    # Generate 14 consecutive dates starting from start_date
    dates = [start_date + timedelta(days=i) for i in range(14)]
    
    # Create DataFrame with dates and additional features
    df = pd.DataFrame({'date': dates})
    
    # Feature engineering
    df['day_of_week'] = df['date'].dt.dayofweek
    df['Month'] = df['date'].dt.month
    
    # Season assignment
    def assign_season(month):
        if month in [12, 1, 2]:
            return 3  # Winter
        elif month in [3, 4, 5]:
            return 0  # Spring
        elif month in [6, 7, 8]:
            return 1  # Summer
        else:
            return 2  # Autumn
    
    df['Season'] = df['Month'].apply(assign_season)
    df['quarter'] = df['date'].dt.quarter
    
    # Holiday check (simplified version)
    holidays = ['01-01', '02-14', '07-04', '11-11', '11-23', '11-27', '11-28', '12-25', '12-31']
    df['Month_Day'] = df['date'].dt.strftime('%m-%d')
    df['is_holiday'] = np.where(df['Month_Day'].isin(holidays), 1, 0)
    
    df['day'] = df['date'].dt.day
    df['year'] = df['date'].dt.year
    
    # Add constant features
    df['minimum_nights'] = min_nights
    df['maximum_nights'] = max_nights
    
    # Add price_lag as the 10th feature, using the average price
    df['price_lag'] = avg_price
    
    # Select and order features exactly as during training
    features = ['minimum_nights', 'maximum_nights', 
                'price_lag',  # Add this back
                'day_of_week', 'Month', 'Season', 
                'quarter', 'is_holiday', 'day', 'year']
    
    return df[features].values

def predict_prices(start_date, avg_price, min_nights, max_nights):
    """
    Predict prices for the next 7 days
    """
    # Generate features
    features = generate_feature_engineering(start_date, avg_price, min_nights, max_nights)
    
    # Reshape for LSTM input (add batch and time steps)
    features_reshaped = features.reshape(1, 14, 10)
    
    # Scale features
    features_scaled = scaler_X.transform(features_reshaped.reshape(-1, 10)).reshape(features_reshaped.shape)
    
    # Predict
    predictions_scaled = model.predict(features_scaled)
    
    # Inverse transform predictions
    predictions = scaler_y.inverse_transform(predictions_scaled)
    
    return predictions.flatten()

# Streamlit App
def main():
    st.title('Airbnb Price Predictor')
    
    # Sidebar inputs
    st.sidebar.header('Input Parameters')
    avg_price = st.sidebar.number_input('Average Price', min_value=0.0, value=100.0, step=10.0)
    min_nights = st.sidebar.number_input('Minimum Nights', min_value=1, value=1)
    max_nights = st.sidebar.number_input('Maximum Nights', min_value=1, value=7)
    start_date = st.sidebar.date_input('Start Date', value=datetime.now())
    
    # Convert start_date to datetime
    start_date = datetime.combine(start_date, datetime.min.time())
    
    # Predict button
    if st.sidebar.button('Predict Prices'):
        try:
            # Get predictions
            predictions = predict_prices(start_date, avg_price, min_nights, max_nights)
            
            # Create dates for predictions
            dates = [start_date + timedelta(days=i+1) for i in range(7)]
            
            # Display predictions in a table
            pred_df = pd.DataFrame({
                '' : ['Day #1', 'Day #2', 'Day #3', 'Day #4', 'Day #5', 'Day #6', 'Day #7'],
                'Date': [date.strftime('%B %d, %Y') for date in dates],  # Format date as desired
                'Predicted Price': [f"${price:.2f}" for price in predictions],
                'Day of the Week': [date.strftime('%A') for date in dates]  # Add day of the week
            })

            styled_pred_df = pred_df.style.hide_index().set_table_styles(
                [{'selector': 'thead th', 'props': [('background-color', '#4CAF50'), ('color', 'white')]}]
            )
            st.table(styled_pred_df)
            
            # st.table(pred_df)
            
            # Plot predictions
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(dates, predictions, marker='o')
            ax.set_title('Predicted Airbnb Prices')
            ax.set_xlabel('Date')
            ax.set_ylabel('Price')
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
        
        # Set the theme
        st.markdown("""
        <style>
            body {
                background-color: #f5f5f5;
                font-family: 'Roboto', sans-serif;
            }
            .stDataFrame {
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                padding: 20px;
            }
            .stDataFrame th, .stDataFrame td {
                padding: 10px;
                text-align: left;
            }
            .stDataFrame th {
                background-color: #f0f0f0;
                font-weight: bold;
            }
        </style>
        """, unsafe_allow_html=True)

# Run the app
if __name__ == '__main__':
    main()
