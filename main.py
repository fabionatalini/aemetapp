from flask import Flask
from flask import request
from flask import render_template
import requests
import pandas

url_meteo_stations = "https://opendata.aemet.es/opendata/api/valores/climatologicos/inventarioestaciones/todasestaciones/"
url_meteo_data_root = "https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/"

#function to connect to aemet open data
def get_connection(path,key):
    return requests.request("GET", path,
                            headers={'cache-control': "no-cache"},
                            params={"api_key":key})

#function to build the html to enter the api key
def ask_for_api_key():
    html="""<form action="" method="get">
    Please enter your API key: <input type="text" name="your_api_key">
    <br><br>
    <input type="submit" value="Submit">
    <input type="reset" value="Reset">
    </form><hr><p>Go back to the <a href='/'>welcome page</a>.</p>"""
    return html

# function to get the stations names and ids and build the html with the select tag
def retrieve_stations(path,key):
    all_meteo_stations = get_connection(path,key)
    stations_uri = all_meteo_stations.json()['datos']
    stations_json = requests.get(stations_uri).json()
    station_names=list()
    station_ids=list()
    for i in range(len(stations_json)):
        prov_name_id = stations_json[i].get("provincia") + " - " + stations_json[i].get("nombre") + " - " + stations_json[i].get("indicativo")
        station_names.append(prov_name_id)
        station_ids.append(stations_json[i].get("indicativo"))
        del prov_name_id, i
    station_names = [x.replace(" ","_") for x in station_names]
    stations_dict = dict(zip(station_names,station_ids))
    tp="".join(list(map(lambda x: "<option>"+x, sorted(station_names))))
    stations_select_list="".join(['<select name="chosen_station">', tp, '</select>'])
    return stations_dict, stations_select_list

#function to build the html to select the station
def ask_for_station(key,string):
    html="""<form action="" method="get">
    Got API key: <input type="text" name="your_api_key" value="""+key+""" readonly>
    <br><br>
    Select the meteo station: """+string+"""
    <br><br>
    <input type="submit" value="Submit">
    <input type="reset" value="Reset">
    </form><hr><p>Go back to the <a href='/'>welcome page</a>.</p>"""
    return html

#function to build the html to select the dates
def ask_for_dates(key,station):
    html="""<form action="" method="get">
    Got API key: <input type="text" name="your_api_key" value="""+key+""" readonly>
    <br><br>
    Meteo station: <input type="text" name="chosen_station" value="""+station+""" readonly>
    <br><br>
    Select start date: <input type="date" name="date_start">
    Select end date: <input type="date" name="date_end">
    <br><br>
    <input type="submit" value="Submit">
    <input type="reset" value="Reset">
    </form><hr><p>Go back to the <a href='/'>welcome page</a>.</p>"""
    return html
 
#function to retrieve meteo data
def retrieve_meteo_data(root_url,start,end,id_station,key):
    url_data = root_url+"fechaini/"+start+"T00:00:00UTC/fechafin/"+end+"T23:59:59UTC/estacion/"+id_station+"/"
    response = get_connection(url_data, key)
    try:
        data_uri = response.json()['datos']
        result = requests.get(data_uri).json()
    except:
        return str(response.json()['descripcion'])
    fechas = list(map(lambda x: x.get('fecha'), result))
    precipi = list(map(lambda x: x.get('prec'), result))
    tempem = list(map(lambda x: x.get('tmed'), result))
    l = list(zip(fechas,precipi,tempem))
    df = pandas.DataFrame(l, columns=['fecha','precipi','tempem'])
    df['month'] = pandas.DatetimeIndex(df['fecha']).month
    for c in ['precipi','tempem']:
        y=list()
        for i in range(len(df)):
            try:
                y += [float(df.loc[i, c].replace(',', '.'))]
            except:
                y+=[0]
        df[c]=y
    tempem=list(df.groupby(['month']).mean()['tempem'])
    precipi=list(df.groupby(['month']).sum()['precipi'])
    daily_data=df.iloc[:,0:3].to_csv(path_or_buf=None, header=True, index=False)
    return {'tempem':tempem, 'precipi':precipi, 'daily_data':daily_data}


#initialize the app
app = Flask(__name__)

@app.route("/")
def welcome_page():
    return render_template('welcome_page.html')

@app.route("/aemetapp")
def index():
    your_api_key = request.args.get("your_api_key", "")
    if not your_api_key:
        return ask_for_api_key()
    else:
        chosen_station = request.args.get("chosen_station", "")
        if not chosen_station:
            stations_dict, stations_select_list = retrieve_stations(path=url_meteo_stations, key=your_api_key)
            return ask_for_station(key=your_api_key,string=stations_select_list)
        else:
            date_start = request.args.get("date_start", "")
            date_end = request.args.get("date_end", "")
            if not date_start or not date_end:
                return ask_for_dates(key=your_api_key,station=chosen_station)
            else:
                stations_dict, stations_select_list = retrieve_stations(path=url_meteo_stations, key=your_api_key)
                station_id = stations_dict.get(chosen_station)
                meteo_data_to_render = retrieve_meteo_data(url_meteo_data_root, date_start, date_end, station_id, your_api_key)
                if isinstance(meteo_data_to_render, dict):
                    meteo_data_to_render['station'] = chosen_station
                    meteo_data_to_render['from_to_dates'] = "From " + date_start + " to " + date_end
                    return render_template('make_chart.html', meteo_data_to_render=meteo_data_to_render)
                else:
                    return meteo_data_to_render


                
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
