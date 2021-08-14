import math
import pandas as pd
import numpy as np
from geopy.distance import distance, geodesic, great_circle


cols = ['longitude', 'latitude', 'dist', 'trip_distance',
        'time_of_day', 'day_of_week', 'passenger_count',
        'dayofmonth', 'dayofyear']
dtypes = [float, float, float, float, int, str,
          int, int, int]
dtype = dict(zip(cols, dtypes))
# print(dtype)


def calculate_distance(pickup, dropoff):
    # newport_ri = (40.795921, -73.970932)
    # cleveland_oh = (40.789124, -73.970169)
    dist1 = geodesic(pickup, dropoff, ellipsoid='WGS-84').miles
    dist2 = distance(pickup, dropoff, ellipsoid='WGS-84').miles
    dist3 = great_circle(pickup, dropoff, ).miles
    return dist1, dist2, dist3


def prepare_data(pickup, dropoff, trip_dist, dt, tmd, passenger):
    longg = pickup[1] - dropoff[1]
    lat = pickup[0] - dropoff[0]
    dist = math.sqrt(math.pow(longg, 2) + math.pow(lat, 2))
    longitude = math.sqrt(math.pow(longg, 2))
    ltitude = math.sqrt(math.pow(lat, 2))
    time_of_day = tmd.hour
    day_of_week = pd.to_datetime(dt).day_name()
    dayofmonth = dt.day
    dayofyear = pd.to_datetime(dt).dayofyear
    val = [longitude, ltitude, dist, trip_dist, time_of_day,
           day_of_week, passenger, dayofmonth, dayofyear]
    data = pd.DataFrame(np.array([val]), columns=cols)
    data = data.astype(dtype)
    # print(data.values.tolist())
    return data
