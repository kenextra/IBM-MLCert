import math
import pandas as pd
from pyproj import Geod


# Bounding latitude/longitude
lat = [40.5612, 40.9637]
lon = [-74.1923, -73.5982]

Payment_Type = {"1": "Credit card",
                "2": "Cash",
                "3": "No charge",
                "4": "Dispute",
                "5": "Unknown",
                "6": "Voided trip", }

RateCode = {"1": "Standard rate",
            "2": "JFK",
            "3": "Newark",
            "4": "Nassau or Westchester",
            "5": "Negotiated fare",
            "6": "Group ride",
            "99": "99"}

VendorID = {"1": "Creative Mobile Technologies, LLC",
            "2": "VeriFone Inc.", }


def load_data(path_dir=None, filename=None, parse_dates=None,
              usecols=None, dtype=None, low_memory=False,
              file_substr='yellow', skiprows=0, preprocess=False):
    if filename:
        print(f"Loading {filename}...\n")
        df = pd.read_csv(path_dir / filename, parse_dates=parse_dates,
                         names=usecols, dtype=dtype, low_memory=False,
                         skiprows=skiprows)
    else:
        print(f"Loading all {file_substr}*.csv in {path_dir} folder...\n")
        df_from_each_file = (pd.read_csv(f, parse_dates=parse_dates,
                                         names=usecols, dtype=dtype,
                                         low_memory=False,
                                         skiprows=skiprows)
                             for f in path_dir.iterdir()
                             if f'{file_substr}' in str(f))
        df = pd.concat(df_from_each_file, ignore_index=True)
    if preprocess:
        df = basic_preprocessing(df)
    df.reset_index(inplace=True, drop=True)
    return df


def basic_preprocessing(df=None):
    print('Converting categorical features to their corresponding values...\n')
    df.loc[:, 'payment_type'] = df['payment_type'].apply(lambda x: Payment_Type[x])
    df.loc[:, 'RateCodeID'] = df['RateCodeID'].apply(lambda x: RateCode[x])
    df.loc[:, 'VendorID'] = df['VendorID'].apply(lambda x: VendorID[x])

    # Remove invalid charges
    # Only keep trips (rows) containing valid charges.
    print('Removing invalid charges...\n')
    df.query('RateCodeID != "99"', inplace=True)
    df.query('fare_amount > 0', inplace=True)
    df.query('extra >= 0', inplace=True)
    df.query('mta_tax >= 0', inplace=True)
    df.query('tip_amount >= 0', inplace=True)
    df.query('tolls_amount >= 0', inplace=True)
    df.query('improvement_surcharge >= 0', inplace=True)
    df.query('total_amount > 0', inplace=True)

    # Only keep trips where charges match the expected values.
    # ImpSurcharge is $0.30
    # Tax is $0.50
    # Total is the sum of all charges
    df.query('abs(improvement_surcharge-0.3) < 0.01', inplace=True)
    df.query('abs(mta_tax-0.5) < 0.01', inplace=True)
    df.query('abs(fare_amount+extra+mta_tax+tip_amount+tolls_amount+improvement_surcharge-total_amount) < 0.01', inplace=True)

    # Remove invalid trip information
    # Only keep trips with valid passenger and distance information.
    print('Removing invalid trip information...\n')
    df.query('passenger_count > 0', inplace=True)
    df.query('trip_distance > 0', inplace=True)

    # Remove outliers
    # Only keep trips with pickup and drop off locations inside the region of interest.
    print('Keep trips with pickup and drop off locations inside the region of interest\n')
    df.query(f'pickup_longitude >= {lon[0]} & pickup_longitude <= {lon[1]}', inplace=True)
    df.query(f'dropoff_longitude >= {lon[0]} & dropoff_longitude <= {lon[1]}', inplace=True)
    df.query(f'pickup_latitude >= {lat[0]} & pickup_latitude <= {lat[1]}', inplace=True)
    df.query(f'dropoff_latitude >= {lat[0]} & dropoff_latitude <= {lat[1]}', inplace=True)

    # Add trip features
    # Add two new variables to the table
    # Duration - Length of the trip, in minutes calculated from the pickup and drop off times.
    # AveSpeed - Average speed, in mph, calculated from the distance and duration values.
    print('Adding new features: Duration...\n')
    df['duration'] = pd.to_timedelta((df.tpep_dropoff_datetime - df.tpep_pickup_datetime),
                                     unit='minutes').dt.seconds / 60

    # Only keep trips with typical values
    # Typical trip
    print('Only keep trips with typical values..\n')
    df.query('duration >= 1 & duration <= 120', inplace=True)
    df.query('trip_distance >= 0.01 & trip_distance <= 50', inplace=True)

    # Typical charges
    df.query('fare_amount >= 0.01 & fare_amount <= 100', inplace=True)
    df.query('tolls_amount <= 20', inplace=True)
    df.query('total_amount >= 0.5 & total_amount <= 120', inplace=True)

    df.reset_index(inplace=True, drop=True)
    return df


def add_avespeed(df):
    df['ave_speed'] = (60 * df.trip_distance) / df['duration']
    df.query('ave_speed >= 0.1 & ave_speed <= 100', inplace=True)
    df.reset_index(inplace=True, drop=True)
    return df


def add_dayof_week(df):
    # Determine day of the week of pick up date
    # This feature is a categoical array indicating the day of the week the trip began,
    # in long format (e.g. 'Monday')
    df['day_of_week'] = df['tpep_pickup_datetime'].dt.day_name()
    df.reset_index(inplace=True, drop=True)
    return df


def add_timeof_day(df):
    # Calculate time of day of pick up
    # This feature represents pick up time as the elapsed time since midnight in decimal hours
    # (e.g. 7:10 am becomes 7.1667)
    col = 'tpep_pickup_datetime'
    numerator = df[col] - df[col].dt.normalize()
    denominator = pd.Timedelta(hours=1)
    df['time_of_day'] = numerator / denominator
    df.reset_index(inplace=True, drop=True)
    return df


def add_crow_direction(df):
    """
    Calculate trip direction
    This feature represents the direction of travel, and is found by taking
    the angle between North and the line connecting trip pick up and drop off locations.
    CrowDirection is in units of degrees and increases clockwise from North.
    """
    g = Geod(ellps='WGS84')
    df['crow_direction'] = df.apply(azimuthal, axis=1, args=[g])
    df.reset_index(inplace=True, drop=True)
    return df


def add_crow_distance(df):
    """
    This feature is the straight line distance in miles between trip pick up and drop off locations.
    Because the earth is a curved surface, arclength is used
    The arclength is converted to miles using the deg2sm function.
    """
    df.reset_index(inplace=True, drop=True)
    return df


def azimuthal(x, g):
    az, _, _ = g.inv(lons1=x['pickup_longitude'],
                     lats1=x['pickup_latitude'],
                     lons2=x['dropoff_longitude'],
                     lats2=x['dropoff_latitude'])
    return az


def sin_azimuth(x):
    return math.sin(math.radians(x['azimuth']))


def add_toll_source(df):
    # add toll source
    # adds the feature TollSource to taxiTable.
    # This feature is a categorical array indicating the source of the toll charges.
    # Known toll amounts for each source are compared to the charged amount to determine the source(s).
    df['toll_source'] = df['tolls_amount']
    # Names of the various toll sources to classify
    sources = ['NoToll', 'CBGH', 'HH', 'VN', 'MTA_Other', 'CBGH_MTA_Other',
               'HH_MTA_Other', 'VN_MTA_Other', 'NYPA',
               'NYPA_MTA_Other', 'OtherToll']

    # Convert multiple rates to the corresponding EZ-pass off-peak rate captured in tolls.
    tolls = [0, 2, 2.44, 10.66, 5.33, 7.33, 7.77, 15.99, 9.75, 15.08, 999, ]
    tollconversions = [[4, 3.75, 7.50, 2.08, 4.16, 8.00], [4.88, 5, 10, 2.54, 5.08, 5.50, 11],
                       [15, 11.08, 16], [5.54], [7.62], [8.08], [16.62],
                       [11.75, 10.50, 12.50], [17.08, 16.04, 18.04, 15.29, 17.29],
                       ]
    # Use latitude to determine source of $7.50/$8 tolls
    # If pick up and drop off locations are North of CBGH, assign MTA_Other rate
    query1 = df.toll_source.isin([7.50, 8])
    query2 = (df.pickup_latitude > 40.617) & (df.dropoff_latitude > 40.617)
    df.loc[(query1 & query2), 'toll_source'] = 5.33

    # Use longitude to determine source of $10.66/$15/$11.08/$16 tolls
    # If pick up and drop off locations are East of VN, assign MTA_Other rate
    query1 = df.toll_source.isin([10.66, 15, 11.08, 16])
    query2 = (df.pickup_longitude > -74.05) & (df.dropoff_longitude > -74.05)
    df.loc[(query1 & query2), 'toll_source'] = 5.33

    for toll, conv in zip(tolls[1:-1], tollconversions):
        df.loc[df.toll_source.isin(conv), 'toll_source'] = toll

    # Change all unknown toll charges to NaN.
    df.loc[~df.toll_source.isin(tolls), 'toll_source'] = 999

    # Convert TollSource to a categorical and replace the amounts with source names
    cat = dict(zip(tolls, sources))
    df.loc[:, 'toll_source'] = df['toll_source'].apply(lambda x: cat.get(x))
    df.reset_index(inplace=True, drop=True)
    return df


def add_toll_paid(df):
    df.loc[:, 'toll_paid'] = df.tolls_amount > 0
    df.loc[df.toll_paid.isin([True]), 'toll_paid'] = "Toll"
    df.loc[df.toll_paid.isin([False]), 'toll_paid'] = "NoToll"
    df.reset_index(inplace=True, drop=True)
    return df


def filter_toll(df):
    # Only keep trips where a toll was charged
    df.query("toll_source != 'NoToll'", inplace=True)

    # Merge similar toll categories
    df.loc[df.toll_source.isin(["HH", "HH_MTA_Other"]), 'toll_source'] = "HH"
    df.loc[df.toll_source.isin(["VN", "VN_MTA_Other"]), 'toll_source'] = "VN"
    df.loc[df.toll_source.isin(["CBGH", "CBGH_MTA_Other"]), 'toll_source'] = "CBGH"
    df.loc[df.toll_source.isin(["NYPA", "NYPA_MTA_Other"]), 'toll_source'] = "NYPA"

    # Rename MTA_Other and OtherToll classes.
    df.loc[df.toll_source.isin(["MTA_Other"]), 'toll_source'] = "MTA"
    df.loc[df.toll_source.isin(["OtherToll"]), 'toll_source'] = "Other"
    df.reset_index(inplace=True, drop=True)
    return df
