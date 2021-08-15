import streamlit as st
import pandas as pd
import folium
import joblib
from helper import calculate_distance, prepare_data
# from folium.plugins import HeatMap
from streamlit_folium import folium_static
# import time
# import datetime
from datetime import datetime


# Load model
@st.cache(allow_output_mutation=True)
def load_model():
    my_model = joblib.load('model.joblib')
    return my_model


model = load_model()

# st.title("""New York City Map""")
st.markdown("<h1 style='text-align: center; color: black;'>New York City Map</h1>", unsafe_allow_html=True)

st.sidebar.header('Taxi Trip Details')
dt = st.sidebar.date_input('Date')
tmd = st.sidebar.time_input('Time Of Day', value=datetime.now().time())

# st.sidebar.subheader('Pickup Coordinates')
st.sidebar.write("""#### Pickup Coordinates""")
pick_lat = st.sidebar.number_input('Latitude',
                                   min_value=40.5612, max_value=40.9637,
                                   key='Latitude', format='%.4f')
pick_long = st.sidebar.number_input('Longitude',
                                    min_value=-74.1923, max_value=-73.5982,
                                    key='Longitude', format='%.4f')

# st.sidebar.subheader('Dropoff Coordinates')
st.sidebar.write("""#### Dropoff Coordinates""")
drop_lat = st.sidebar.number_input('Latitude', min_value=40.5612,
                                   max_value=40.9637, format='%.4f')
drop_long = st.sidebar.number_input('Longitude', min_value=-74.1923,
                                    max_value=-73.5982, format='%.4f')


dist1, dist2, dist3 = calculate_distance((pick_lat, pick_long), (drop_lat, drop_long))
# st.sidebar.write("""#### Distance (miles)""")
# st.sidebar.write(f"{dist1} miles")
# st.sidebar.write(f"{dist2} miles")
# st.sidebar.write(f"{dist3} miles")

st.sidebar.number_input('Distance (miles)', value=dist1)
# st.sidebar.header('Trip Duration')

passenger = st.sidebar.number_input('Passenger Count', min_value=1,
                                    max_value=9, step=1, value=1)

st.sidebar.write("""### Trip Duration""")
col1, col2 = st.sidebar.beta_columns(2)
with col1:
    duration = st.button('Predict')

prepared_data = prepare_data((pick_lat, pick_long), (drop_lat, drop_long),
                             dist1, dt, tmd, passenger, )
with col2:
    if duration:
        dur = model.predict(prepared_data)[-1]
        st.write(f"{dur:.2f} +/- 4.00 minutes")

# Plot Map
data = pd.DataFrame({'latitude': [pick_lat, drop_lat, ],
                     'longitude': [pick_long, drop_long, ]
                     },
                    index=['Pickup', 'Dropoff'],)

st.map(data=data, zoom=9)


# map_heatmap = folium.Map(location=[pick_lat, pick_long], zoom_start=11)
# st.subheader("Heatmap")
# folium_static(map_heatmap)

st.write("\n\n")
st.markdown("<h3 style='text-align: center; color: black;'>Data supplied by user for prediction</h3>",
            unsafe_allow_html=True)
cols1 = ['time_of_day', 'day_of_week', 'dayofmonth', 'dayofyear', ]
cols2 = ['longitude', 'latitude', 'dist', 'trip_distance', ]
st.table(prepared_data[cols1], )
st.table(prepared_data[cols2], )

# Select coordinates
_, col2, _ = st.beta_columns([1, 3, 2])
with col2:
    st.dataframe(data)

# st.table(data)

_, col2, _ = st.beta_columns(3)
with col2:
    st.button('Pick Coordinates')
