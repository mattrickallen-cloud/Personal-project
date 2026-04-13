from pygbif import species as species
from pygbif import occurrences as occ
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import pycountry
import numpy as np
import streamlit as st

st.title("Biodiversity evolution automatic model")
def haversine(lon1, lat1, lon2, lat2):
    R = 6371
    lon1, lat1, lon2, lat2 = np.radians([lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

config_species = {
    "Chordata":
    {"limit": 500,
    "min_points": 5},

    "Arthropoda":
    {"limit": 2000,
    "min_points": 1},

    "Annelida":
    {"limit": 1500,
    "min_points": 30}
    }

chosen_species_name = st.text_input("Enter the scientific name of chosen species (ex: Lynx pardinus).")
country_names = st.text_input("Enter the chosen country of study (ex: Spain).")
    
chosen_species = species.name_backbone(scientificName=chosen_species_name)
taxonkey = chosen_species["usage"]["key"]
phylum = chosen_species["classification"][1]["name"]
country_list = [country_names]
#region_code = "FRA.1_1"
results = []
country = pycountry.countries.get(name=country_names).alpha_2

world = gpd.read_file("https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip")
country_map = world[world["NAME"].isin(country_list)]
#region_link = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements/95-val-d-oise/departement-95-val-d-oise.geojson"
#region_map = gpd.read_file(region_link)
#region_map = region_map.to_crs(epsg=4326)
#zone = "POLYGON((1.6 48.9, 2.6 48.9, 2.6 49.2, 1.6 49.2, 1.6 48.9))"

fig1 = plt.figure(1, figsize=(12, 8))
ax_map = plt.gca()

country_map.plot(ax=ax_map)
#region_map.plot(ax=ax_map, color='whitesmoke', edgecolor='black', linewidth=1.5)
cmap = plt.get_cmap("hot")

for offset in range(0, 10000, config_species[f"{phylum}"]["limit"]):

    occdata = occ.search(
                        taxonKey=taxonkey,
                        hasCoordinate=True,
                        limit=config_species[f"{phylum}"]["limit"],
                        offset=offset,
                        #gadmGid=region_code,
                        country=country,
                        #geometry=zone
                        )

    results.extend(occdata["results"])

df = pd.DataFrame(results)
df = df[["decimalLatitude","decimalLongitude","year"]]

if df.empty :
    print(f"No or not enough data for {chosen_species_name} in {country_names}.")
    exit()

df = df.drop_duplicates(subset=["decimalLatitude", "decimalLongitude"])
df = df.dropna(subset=["decimalLatitude", "decimalLongitude"])
df = df[(df["year"] >= 1945) & (df["year"] <= 2026)]
df = df.groupby('year').filter(lambda x: len(x) >= config_species[f"{phylum}"]["min_points"])

if df.empty :
    print(f"No or not enough data for {chosen_species_name} in {country_names}.")
    exit()

df = df.reset_index(drop=True)

year_min = int(df["year"].min())
year_max = int(df["year"].max())

actual_norm = colors.Normalize(vmin=year_min, vmax=year_max)

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

    geometry = [Point(xy) for xy in zip(df_year["decimalLongitude"], df_year["decimalLatitude"])]

    gdf = gpd.GeoDataFrame(df_year,
                        geometry=geometry,
                        crs="EPSG:4326"
                        )

    #hull = gdf.union_all().convex_hull

    #gpd.GeoSeries([hull]).plot(
     #                       ax=ax_map,
    #                        color=cmap(actual_norm(year)),
     #                       alpha=0.2,
      #                      edgecolor=cmap(actual_norm(year))
       #                     )

    gdf.plot(ax=ax_map, markersize=5,color=cmap(actual_norm(year)))

    ax_map.scatter(
                df_year["decimalLongitude"].mean(),
                df_year["decimalLatitude"].mean(),
                s=100,
                color=cmap(actual_norm(year)),
                marker="X",
                edgecolors="black"
                )

    mean_coord["longitude_means"].append(df_year["decimalLongitude"].mean())
    mean_coord["latitude_means"].append(df_year["decimalLatitude"].mean())
    mean_coord["years"].append(year)

country_map = country_map.to_crs(gdf.crs)

sm = plt.cm.ScalarMappable(cmap=cmap, norm=actual_norm)
sm.set_array([])
cbar = plt.colorbar(sm, ax=ax_map)
cbar.set_label("Year")
ax_map.set_title(f"Occurrences of {chosen_species_name} in {country_names} ({year_min}-{year_max})")
if country_names == "France":
    ax_map.set_xlim(-10, 10)
    ax_map.set_ylim(40, 60)
else:
    ax_map.set_xlim(df["decimalLongitude"].min() - 3, df["decimalLongitude"].max() + 3)

plt.legend()

fig2 = plt.figure(2, figsize=(10, 6))

plt.plot(
        mean_coord["years"],
        mean_coord["latitude_means"],
        color="red"
        )

plt.legend()

fig3 = plt.figure(3, figsize=(10, 6))

plt.plot(
        mean_coord["years"],
        mean_coord["longitude_means"],
        color="green"
        )

plt.legend()

fig4 = plt.figure(4)

plt.plot(
        range(year_min,year_max+1),
        year_number,
        color="blue"
        )
percent_max = max(year_number)
percent_year = [0]*len(year_number)
for index in range(len(year_number)):
    percent_year[index] = 1 + year_number[index]/percent_max

plt.legend()

st.pyplot(fig4)

if len(mean_coord["years"]) > 1:

    lon_debut = mean_coord["longitude_means"][0]
    lat_debut = mean_coord["latitude_means"][0]
    lon_fin = mean_coord["longitude_means"][-1]
    lat_fin = mean_coord["latitude_means"][-1]

    distance_km = haversine(lon_debut, lat_debut, lon_fin, lat_fin)
    time = mean_coord["years"][-1] - mean_coord["years"][0]
    speed = distance_km/time

    print(f"{chosen_species_name} has travelled {distance_km} km")
    print(f"Movement speed : {speed} km per year.")

if len(mean_coord["years"]) > 2:

    y = np.array(mean_coord["years"])#*percent_year
    lat = np.array(mean_coord["latitude_means"])
    long = np.array(mean_coord["longitude_means"])
    
    c, d = np.polyfit(y, lat, 1)
    correlation_matrix_lat = np.corrcoef(y, lat)
    correlation_xy_lat = correlation_matrix_lat[0, 1]
    r_squared_lat = correlation_xy_lat**2

    plt.figure(2)    
    
    plt.plot(
            y,            
            c * y + d,
            "b--",
            label=f"R²={r_squared_lat}"
            )
    
    plt.legend()
    
    st.pyplot(fig2)
    
    a, b = np.polyfit(y, long, 1)
    correlation_matrix_long = np.corrcoef(y, long)
    correlation_xy_long = correlation_matrix_long[0, 1]
    r_squared_long = correlation_xy_long**2

    plt.figure(3)
    
    plt.plot(
            y,
            a * y + b,
            "b--",
            label=f"R²={r_squared_long}"
            )
    
    plt.legend()
    
    st.pyplot(fig3)

    year_predict = st.number_input("For which coming year do you want to predict the evolution of this population ?")
    y_lat_pred = c * year_predict + d
    y_long_pred = a * year_predict + b

    ax_map.scatter(y_long_pred,
                y_lat_pred,
                s=200,
                color="green",
                marker="X",
                edgecolors="green",
                label="Predicted average distribution"
                )
    
    plt.legend()

    st.pyplot(fig1)
