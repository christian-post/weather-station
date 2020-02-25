import requests
import logging

def get_weather_data(api_key, city_name):
    base_url = 'https://api.openweathermap.org'
    complete_url = f'{base_url}/data/2.5/weather?q={city_name}&appid={api_key}'
    try:
        response = requests.get(complete_url)
        logging.debug('received weather data')
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.warning(e)
        fallback = {
            'main': {},
            'weather': [
                {
                    'id': 0,
                    'main': 'Null',
                    'description': 'Null',
                    'icon': ''
                }
            ],
            'wind': {},
            'clouds': {},
            'sys': {}
        }
        return fallback


def get_forecast_data(api_key, city_name):
    base_url = 'https://api.openweathermap.org'
    complete_url = f'{base_url}/data/2.5/forecast?q={city_name}&appid={api_key}'
    try:
        response = requests.get(complete_url)
        logging.debug('received forecast data')
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.warning(e)
        fallback = {
            'list': []
        }
        return fallback
