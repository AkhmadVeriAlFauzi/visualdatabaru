import streamlit as st
from pymongo import MongoClient
import pandas as pd
import altair as alt
import json
from datetime import datetime
import pytz
from dateutil import parser

# --- Koneksi MongoDB pakai secrets ---
mongo_uri = st.secrets["mongodb"]["uri"]
mongo_db = st.secrets["mongodb"]["database"]
mongo_coll = st.secrets["mongodb"]["collection"]

client = MongoClient(mongo_uri)
dbcuaca = client[mongo_db]

# Fungsi konversi ke WIB
def convert_to_wib(utc_input):
    try:
        if not utc_input:
            return "Tidak tersedia"
        if isinstance(utc_input, str):
            dt_utc = parser.parse(utc_input)
        elif isinstance(utc_input, datetime):
            dt_utc = utc_input
        else:
            return "Format tidak dikenali"
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=pytz.utc)
        wib = pytz.timezone('Asia/Jakarta')
        dt_wib = dt_utc.astimezone(wib)
        return dt_wib.strftime("%d %b %Y %H:%M WIB")
    except:
        return "Format tidak dikenali"

# Ambil dan parse data cuaca
cuaca_data_raw = list(dbcuaca[mongo_coll].find())

for item in cuaca_data_raw:
    suhu_str = item.get('suhu', '0')
    try:
        item['suhu'] = int(suhu_str.split()[0])
    except:
        item['suhu'] = 0

# --- UI Streamlit ---
st.title("Detail Prediksi Cuaca Per Hari ini")
search_daerah = st.text_input("Masukkan daerah (kota/kab/kec/kel):").lower()
mode = st.radio("Pilih Tampilan:", ('card', 'chart'))

if search_daerah:
    cuaca_data = [
        item for item in cuaca_data_raw
        if search_daerah in (item.get('provinsi') or '').lower()
        or search_daerah in (item.get('kab_kota') or '').lower()
        or search_daerah in (item.get('kecamatan') or '').lower()
        or search_daerah in (item.get('kelurahan') or '').lower()
    ]
else:
    cuaca_data = cuaca_data_raw

df = pd.DataFrame(cuaca_data)

if mode == 'card':
    provinsi_groups = df.groupby('provinsi')
    for provinsi, group in provinsi_groups:
        st.header(provinsi)
        for _, row in group.iterrows():
            suhu = row['suhu']
            icon = "☀️" if suhu >= 32 else ("⛅" if suhu >= 24 else "🌧️")
            st.markdown(f"""
                **{row.get('kab_kota', '')}**  
                {row.get('kecamatan', '')} - {row.get('kelurahan', '')}  
                Suhu: **{suhu}°C** {icon}  
                Cuaca: {row.get('cuaca', 'Tidak tersedia')}  
                Terakhir diperbarui: {convert_to_wib(row.get('timestamp'))}
            """)
            st.markdown("---")
else:
    if df.empty:
        st.info("Data tidak ditemukan untuk filter yang diberikan.")
    else:
        for provinsi, prov_group in df.groupby('provinsi'):
            st.subheader(provinsi)
            for kab_kota, kab_group in prov_group.groupby('kab_kota'):
                st.markdown(f"**{kab_kota}**")
                chart = alt.Chart(kab_group).mark_bar().encode(
                    x='kecamatan:N',
                    y='suhu:Q',
                    tooltip=['kecamatan', 'suhu']
                ).properties(
                    width=600,
                    height=300
                )
                st.altair_chart(chart, use_container_width=True)
