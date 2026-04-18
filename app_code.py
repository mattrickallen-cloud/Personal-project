from pygbif import species as species
from pygbif import occurrences as occ
import pandas as pd
import matplotlib.pyplot as plt
import pycountry
import numpy as np
import folium
import streamlit as st
from streamlit_folium import st_folium
import branca.colormap as cm
import matplotlib.colors as mcolors
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

tab1, tab2, tab3 = st.tabs(["🗺️ Map", "📈 Analysis", "⚙️ Other"])

def set_bg_from_url(url):
    st.markdown(
        f"""<style>.stApp {{
            background-image: url('{url}');
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Exemple avec une image de Lynx hébergée sur le web
Url = "https://images.pexels.com/photos/13641027/pexels-photo-13641027.jpeg"
set_bg_from_url(Url)

#config_species = {
 #   "Chordata":
  #  {"limit": 500,
   # "min_points": 5},

    #"Arthropoda":
    #{"limit": 2000,
    #"min_points": 1},

    #"Annelida":
    #{"limit": 1500,
    #"min_points": 30},       
    
    #"Plantae":
    #{"limit":500,
    # "min_points":5}
    #}
with st.sidebar:
    st.header("Parameters")
    st.divider()
    chosen_species_name = st.text_input("Enter the scientific name of chosen species (ex: Lynx pardinus).")
    country_names = st.text_input("Enter the chosen country of study (ex: Spain).")
    year_predict = st.number_input("For which coming year do you want to predict the evolution of this population ?")
    st.divider()
    run_button = st.button("Run the simulation.")

if run_button:
 
    with st.spinner("Collecting GBIF data..."):
     
        chosen_species = species.name_backbone(scientificName=chosen_species_name)
     
        if not chosen_species or chosen_species["diagnostics"]["matchType"]=="NONE":
         
           st.error(f"'{chosen_species_name}' not found, check spelling.")
           st.stop()
         
        taxonkey = chosen_species["usage"].get("key")
        #phylum = chosen_species["classification"][1]["name"]
        country_list = [country_names]
        results = []
        country = pycountry.countries.get(name=country_names)
      
        if country is None:
        
           st.error("Country not found")
           st.stop()

        country_alpha2 = country.alpha_2
     
        for offset in range(0, 10000, 500):
        
            occdata = occ.search(
                                taxonKey=taxonkey,
                                hasCoordinate=True,
                                limit=500,
                                offset=offset,
                                country=country_alpha2,
                                )
        
            results.extend(occdata["results"])
        
        df = pd.DataFrame(results)
        df = df[["decimalLatitude","decimalLongitude","year"]]
        
        if df.empty:
         
            print(f"No or not enough data for {chosen_species_name} in {country_names}.")
            exit()
        
        df = df.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"])
        df = df.dropna(subset=["decimalLatitude", "decimalLongitude"])
        df = df[(df["year"] >= 1500) & (df["year"] <= 2026)]
        df = df.groupby('year').filter(lambda x: len(x) >= 5)
        
        if df.empty:
         
            print(f"No or not enough data for {chosen_species_name} in {country_names}.")
            exit()
        
        df = df.reset_index(drop=True)
        
        year_min = int(df["year"].min())
        year_max = int(df["year"].max())
        
        mean_coord = {
                    "longitude_means" : [],
                    "latitude_means" : [],
                    "years" : []
                    }
        
        year_number = [0]*((year_max+1)-year_min)
     
        for year in range(year_min,year_max+1):
        
            df_year = df[df["year"] == year]
        
            if df_year.empty:
             
                continue
        
            year_number[year-year_min] = len(df_year)
        
            mean_coord["longitude_means"].append(df_year["decimalLongitude"].mean())
            mean_coord["latitude_means"].append(df_year["decimalLatitude"].mean())
            mean_coord["years"].append(year)
        
        m = folium.Map(
                location=[df["decimalLatitude"].mean(), df["decimalLongitude"].mean()],
                zoom_start=6,
                tiles="cartodbpositron"
                      )

        cmap_plt = plt.get_cmap('YlOrRd')
        colors_hex = [mcolors.to_hex(cmap_plt(i)) for i in np.linspace(0, 1, 256)]
        colormap = cm.LinearColormap(
                                    colors=colors_hex,
                                    vmin=df['year'].min(),
                                    vmax=df['year'].max(),
                                    caption="Occurrence Years"
                                    )
        colormap.add_to(m)
        
        fg_obs = folium.FeatureGroup(name="Individual occurences").add_to(m)
     
        for _, row in df.iterrows():
        
            point_color = colormap(row['year'])
            
            folium.CircleMarker(
                                location=[row["decimalLatitude"], row["decimalLongitude"]],
                                radius=3,
                                color=point_color,
                                weight=0.5,
                                fill=True,
                                fill_color=point_color,
                                fill_opacity=0.9,
                                tooltip=f"Year : {int(row['year'])}"
                                ).add_to(fg_obs)
        
        history_group = folium.FeatureGroup(name="Means").add_to(m)
        
        for lon, lat, yr in zip(mean_coord["longitude_means"], mean_coord["latitude_means"], mean_coord["years"]):
         
            folium.Marker(
                          location=[lat, lon],
                          icon=folium.Icon(color=point_color, icon="info-sign"),
                          popup=f"Mean position in {yr}"
                         ).add_to(history_group)
        
        fg_traj = folium.FeatureGroup(name="Mean trajectory").add_to(m)
        points_trajectoire = list(zip(mean_coord["latitude_means"], mean_coord["longitude_means"]))
            
        folium.PolyLine(points_trajectoire, color="red", weight=2, opacity=0.8).add_to(fg_traj)
        
        folium.TileLayer('openstreetmap').add_to(m)
        
        
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                        attr='Esri', name='Satellite'
                        ).add_to(m)
        
        
        folium.LayerControl().add_to(m)
        
        fig2 = plt.figure(2, figsize=(10, 6))
        
        plt.plot(
                mean_coord["years"],
                mean_coord["latitude_means"],
                color="red",
                label="Mean latitude evolution"
                )
        
        plt.legend()
        
        fig3 = plt.figure(3, figsize=(10, 6))
        
        plt.plot(
                mean_coord["years"],
                mean_coord["longitude_means"],
                color="green",
                label="Mean longitude evolution"
                )
        
        fig4 = plt.figure(4)
        
        plt.plot(
                range(year_min,year_max+1),
                year_number,
                color="blue",
                label="Number of occurences through time"
                )
        
        plt.legend()
         
        if len(mean_coord["years"]) > 2:
        
            y1 = np.array(mean_coord["years"])
            lat1 = np.array(mean_coord["latitude_means"])
            long1 = np.array(mean_coord["longitude_means"])

            counts = np.array([year_number[yr - year_min] for yr in mean_coord["years"]])
            weights = counts/np.max(counts)
            
            c, d = np.polyfit(y1, lat1, 1, w=weights)
            correlation_matrix_lat = np.corrcoef(y1, lat1)
            correlation_xy_lat = correlation_matrix_lat[0, 1]
            r_squared_lat = correlation_xy_lat**2
        
            plt.figure(2) 

            y2 = np.array(mean_coord["years"]).reshape(-1, 1)
            lat2 = np.array(mean_coord["latitude_means"])
            
            poly_lat = PolynomialFeatures(degree=2)
            y2_poly_lat = poly_lat.fit_transform(y2)
            
            model = LinearRegression()
            model.fit(y2_poly_lat, lat2)
            lat2_pred = model.predict(y2_poly_lat)
            score_lat2 = r2_score(lat2, lat2_pred)

            if r_squared_lat >= score_lat2:
                
                lat_pred =  c * y1 + d

            else:
                
                lat_pred = lat2_pred
            
            plt.plot(
                    y1,            
                    lat_pred,
                    "b--",
                    label=f"Linear model, R²={max(r_squared_lat, score_lat2)}"
                    )
            
            plt.legend()
            
            a, b = np.polyfit(y1, long1, 1, w=weights)
            correlation_matrix_long = np.corrcoef(y1, long1)
            correlation_xy_long = correlation_matrix_long[0, 1]
            r_squared_long = correlation_xy_long**2
        
            plt.figure(3)

            long2 = np.array(mean_coord["longitude_means"])
            
            poly_long = PolynomialFeatures(degree=2)
            y2_poly_long = poly_long.fit_transform(y2)
            
            model.fit(y2_poly_long, long2)
            long2_pred = model.predict(y2_poly_long)
            score_long2 = r2_score(long2, long2_pred)
            
            if r_squared_long >= score_long2:
                
                long_pred =  a * y1 + b
                
            else:
                
                long_pred = long2_pred
            
            plt.plot(
                    y1,
                    long_pred,
                    "b--",
                    label=f"Linear model, R²={max(r_squared_long, score_long2)}"
                    )
 
            plt.legend()

            if r_squared_lat >= score_lat2:
                
                y_lat_pred = c * year_predict + d

            else:

                future_year_lat = np.array([[2030]])
                future_year_poly_lat = poly_lat.transform(future_year_lat)
                future_lat_pred = model.predict(future_year_poly_lat)
                y_lat_pred = future_lat_pred[0]

            if r_squared_long >= score_long2:
                
                y_long_pred = a * year_predict + b

            else:

                future_year_long = np.array([[2030]])
                future_year_poly_long = poly_long.transform(future_year_long)
                future_long_pred = model.predict(future_year_poly_long)
                y_long_pred = future_long_pred[0]

            folium.Marker(
                         location=[y_lat_pred, y_long_pred],
                         icon=folium.Icon(color="green", icon="star"),
                         popup=f"Predicted mean position in {year_predict}"
                         ).add_to(m)
        
            plt.legend()

            with tab1:
             
                st.subheader("Interactice map")
                st.divider()
                
                if not df.empty:
                    
                    st_folium(m, width=700, height=500, returned_objects=[])
                    
        with st.sidebar:
        
            st.success("Simulation done !")


        with tab2:
         
            st.subheader("Tendancy Analysis")
            st.divider()
            st.pyplot(fig2)
            st.divider()
            st.pyplot(fig3)
        
        with tab3:
                 
            st.subheader("Relevant Information")
            st.divider()
            st.write(f"Species : {chosen_species_name}")
            st.write(f"Prediction year : {year_predict}")
            st.pyplot(fig4)
                        
