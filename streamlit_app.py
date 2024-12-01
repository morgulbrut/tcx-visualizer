import streamlit as st
import pandas as pd
from dateutil import parser
from scipy.signal import savgol_filter
import pydeck as pdk

import lxml.etree



# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='TCX Visualizer',	
    page_icon=':penguin:', # This is an emoji shortcode. Could be a URL too.
    layout='wide'
)

@st.cache_data
def get_data(file):
    data = file.read()
    xml = lxml.etree.fromstring(data)
    ns = {'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
    # Get the trackpoints
    trackpoints = xml.xpath('//ns:Trackpoint', namespaces=ns)
    initial_time = parser.parse(trackpoints[0].xpath('ns:Time', namespaces=ns)[0].text)
    initial_alt = float(trackpoints[0].xpath('ns:AltitudeMeters', namespaces=ns)[0].text)
    records = [
        {
            'time': int((parser.parse(tp.xpath('ns:Time', namespaces=ns)[0].text) - initial_time).total_seconds()),
            'lat': float(tp.xpath('ns:Position/ns:LatitudeDegrees', namespaces=ns)[0].text),
            'lon':float(tp.xpath('ns:Position/ns:LongitudeDegrees', namespaces=ns)[0].text),
            'alt': float(tp.xpath('ns:AltitudeMeters', namespaces=ns)[0].text),
            'rel_alt': float(tp.xpath('ns:AltitudeMeters', namespaces=ns)[0].text) - initial_alt,
            'ts': tp.xpath('ns:Time', namespaces=ns)[0].text,
            'indx': tp.xpath('ns:Time', namespaces=ns)[0].text.split('T')[1].split('.')[0],
            'distance':float(tp.xpath('ns:DistanceMeters', namespaces=ns)[0].text),
            'heart_rate':int(tp.xpath('ns:HeartRateBpm/ns:Value', namespaces=ns)[0].text)
        }
        for tp in trackpoints
    ]

    df = pd.DataFrame.from_records(records)
    df['speed'] = (df['distance'].diff() / df['time'].diff())*3.6
    df['speed'].fillna(0, inplace=True)
    df.set_index('indx', inplace=True)
    df=df[df['speed'] >= 0]
    df=df[df['speed'] <= 100]
    df=df[df['distance'] > 0]
    return df


st.sidebar.title('Settings')
file = st.sidebar.file_uploader('Upload a TCX file', type=['tcx'])

st.title('TCX Visualizer')

if file:
    df = get_data(file)

    if st.checkbox('Show raw data', value=False):   
        st.subheader('Data')
        st.write(df)

    st.subheader('Map')
    st.map(df[['lat', 'lon']],size = 1, zoom=12,color='#FF6347')

    st.subheader('Time / Altitude')
    st.line_chart(df[['alt']].apply(savgol_filter,  window_length=21, polyorder=2),color='#FF6347')  

    st.subheader('Time / Speed')
    st.line_chart(df[['speed']].apply(savgol_filter,  window_length=51, polyorder=2),color='#FF6347')

    st.subheader('Time / Heart Rate')
    st.line_chart(df[['heart_rate']].apply(savgol_filter,  window_length=51, polyorder=2),color='#FF6347')