import streamlit as st
import pandas as pd
from dateutil import parser
from scipy.signal import savgol_filter
from numpy import interp

from matplotlib import colormaps

import lxml.etree


# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='TCX Visualizer',
    page_icon=':penguin:',  # This is an emoji shortcode. Could be a URL too.
    layout='wide'
)


@st.cache_data
def get_data(file):
    data = file.read()
    xml = lxml.etree.fromstring(data)
    ns = {'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
    # Get the trackpoints
    trackpoints = xml.xpath('//ns:Trackpoint', namespaces=ns)
    initial_time = parser.parse(
        trackpoints[0].xpath('ns:Time', namespaces=ns)[0].text)
    initial_alt = float(trackpoints[0].xpath(
        'ns:AltitudeMeters', namespaces=ns)[0].text)
    records = [
        {
            'time': int((parser.parse(tp.xpath('ns:Time', namespaces=ns)[0].text) - initial_time).total_seconds()),
            'lat': float(tp.xpath('ns:Position/ns:LatitudeDegrees', namespaces=ns)[0].text),
            'lon': float(tp.xpath('ns:Position/ns:LongitudeDegrees', namespaces=ns)[0].text),
            'alt': float(tp.xpath('ns:AltitudeMeters', namespaces=ns)[0].text),
            'rel_alt': float(tp.xpath('ns:AltitudeMeters', namespaces=ns)[0].text) - initial_alt,
            'ts': tp.xpath('ns:Time', namespaces=ns)[0].text,
            'indx': tp.xpath('ns:Time', namespaces=ns)[0].text.split('T')[1].split('.')[0],
            'distance': float(tp.xpath('ns:DistanceMeters', namespaces=ns)[0].text),
            'heart_rate': int(tp.xpath('ns:HeartRateBpm/ns:Value', namespaces=ns)[0].text)
        }
        for tp in trackpoints
    ]

    df = pd.DataFrame.from_records(records)
    df['speed'] = (df['distance'].diff() / df['time'].diff())*3.6
    df['speed'].fillna(0, inplace=True)
    df.set_index('indx', inplace=True)

    df = df[df['speed'] >= 0]
    df = df[df['speed'] <= 100]
    df = df[df['distance'] > 0]

    smooth_window = int(0.0455*len(df))

    df['alt_smooth'] = df[['alt']].apply(
        savgol_filter,  window_length=smooth_window, polyorder=2)
    df['speed_smooth'] = df[['speed']].apply(
        savgol_filter,  window_length=smooth_window, polyorder=2)
    df['heart_rate_smooth'] = df[['heart_rate']].apply(
        savgol_filter,  window_length=smooth_window, polyorder=2)
    df['rel_alt_smooth'] = df[['rel_alt']].apply(
        savgol_filter,  window_length=smooth_window, polyorder=2)
    df['climb_rate_smooth'] = df['alt_smooth'].diff()

    alt_min = df['alt'].min()
    alt_max = df['alt'].max()
    df['alt_color'] = df['alt_smooth'].apply(
        lambda x: tuple(colormaps['magma'].colors[int(interp(x, [alt_min, alt_max], [0, 255]))]))

    df['alt_color'] = df['alt_color'].apply(
        lambda x: f'#{int(x[0]*255):02x}{int(x[1]*255):02x}{int(x[2]*255):02x}')
    return df


st.sidebar.title('Settings')
file = st.sidebar.file_uploader('Upload a TCX file', type=['tcx'])

st.title('TCX Visualizer')

if file:
    df = get_data(file)
    st.write(f"{len(df)} trackpoints found")
    st.write(f"Start time: {df['ts'].iloc[0]}")
    st.write(f"End time: {df['ts'].iloc[-1]}")
    if st.checkbox('Show raw data', value=False):
        st.subheader('Data')
        st.write(df)

    st.subheader('Map')
    st.map(df[['lat', 'lon']], size=1, zoom=12,
           color='#FF6347')

    st.subheader('Time /  Altitude')
    st.line_chart(df[['alt_smooth']], color='#FF6347')

    st.subheader('Time / relative Altitude')
    st.line_chart(df[['rel_alt_smooth']], color='#FF6347')

    st.subheader('Time / Climb Rate')
    st.line_chart(df[['climb_rate_smooth']], color='#FF6347')

    st.subheader('Time / Speed')
    st.line_chart(df[['speed_smooth']], color='#FF6347')

    st.subheader('Time / Heart Rate')
    st.line_chart(df[['heart_rate_smooth']], color='#FF6347')
