import requests

def get_weather_data(api_key, city_name):
    base_url = 'https://api.openweathermap.org'
    complete_url = f'{base_url}/data/2.5/weather?q={city_name}&appid={api_key}'
    #print(complete_url)
    try:
        response = requests.get(complete_url)
        return response.json()
    except Exception:
        print('Could not receive weather data from server.')
        return {}


def get_forecast_data(api_key, city_name):
    base_url = 'https://api.openweathermap.org'
    complete_url = f'{base_url}/data/2.5/forecast?q={city_name}&appid={api_key}'
    #print(complete_url)
    try:
        response = requests.get(complete_url)
        return response.json()
    except Exception:
        print('Could not receive forecast data from server.')
        return {}
