import streamlit as st
import pandas as pd
import folium
import os
from helper import calculate_distance, prepare_data
from streamlit_folium import folium_static
from dotenv import load_dotenv

from googleapiclient import discovery
from google.api_core.client_options import ClientOptions


# Load environmental variables
load_dotenv()

PROJECT_ID = os.environ['PROJECT_ID']
VERSION_NAME = os.environ['VERSION_NAME']
MODEL_NAME = os.environ['MODEL_NAME']
endpoint = 'https://ml.googleapis.com'


# Load model
def make_prediction(data):
    client_options = ClientOptions(api_endpoint=endpoint)
    service = discovery.build('ml', 'v1', client_options=client_options)
    name = f'projects/{PROJECT_ID}/models/{MODEL_NAME}/versions/{VERSION_NAME}'
    instances = data.values.tolist()
    response = service.projects().predict(name=name,
                                          body={'instances': instances}
                                          ).execute()

    if 'error' in response:
        # print(response['error'])
        return response
    return response['predictions'][0]


# st.title("""New York City Map""")
st.markdown("<h1 style='text-align: center; color: black;'>New York City Map</h1>", unsafe_allow_html=True)

st.sidebar.header('Taxi Trip Details')
dt = st.sidebar.date_input('Date')
tmd = st.sidebar.time_input('Time Of Day')

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
        dur = make_prediction(prepared_data)
        st.write(f"{dur:.2f} +/- 4.00 minutes")
        # st.write(dur)

# Plot Map
data = pd.DataFrame({'latitude': [pick_lat, drop_lat, ],
                     'longitude': [pick_long, drop_long, ]
                     },
                    index=['Pickup', 'Dropoff'],)

st.map(data=data, zoom=9)

map_heatmap = folium.Map(location=[pick_lat, pick_long], zoom_start=11)
st.subheader("Heatmap")
folium_static(map_heatmap)

cols1 = ['time_of_day', 'day_of_week', 'dayofmonth', 'dayofyear', ]
cols2 = ['longitude', 'latitude', 'dist', 'trip_distance', ]
st.dataframe(prepared_data[cols1], width=None, height=None)
st.dataframe(prepared_data[cols2], width=None, height=None)

# Select coordinates
_, col2, _ = st.beta_columns([1, 3, 2])
with col2:
    st.dataframe(data)

_, col2, _ = st.beta_columns(3)
with col2:
    st.button('Pick Coordinates')
