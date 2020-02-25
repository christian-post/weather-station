from os import path
import logging
import traceback
import json

import cProfile
import pstats
from pstats import SortKey


filepath = path.dirname(path.abspath(__file__))
logfile = f'{path.basename(__file__).strip(".py")}.log'

logging.basicConfig(filename=path.join(filepath, '..', 'data', logfile), 
                    level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# add logging to console
logging.getLogger().addHandler(logging.StreamHandler())

# define default app settings in case the json file is missing
DEFAULT_SETTINGS = {
    "window_width": 800,
    "window_height": 480,
    "background_color": "#075869",
    "FPS": 10,
    "FPS_plot_mode": 60,
    "clock_size": 96,
    "api_interval_weather": 300,
    "api_interval_forecast": 600,
    "city": "London,UK",
    "indoor_read_interval": 30,
    "repeated_readings": 3,
    "reading_aggregation": "median",
    "device_pin": 4,
    "plot_ytick_intervals": {
        "outdoor_temperature": 2,
        "outdoor_humidity": 5
        },
    "debug_mode": 0,
    "log_mouse_position": 0
    }


def main():
    try:
        from app import App, pygame_quit

        settings_file = path.join(path.join(filepath, '..', 'data', 
                                     'settings.json'))
        if path.isfile(settings_file):
            with open(settings_file, 'r') as f:
                app_settings = json.load(f)
        else:
            logging.info(f'Warning: {settings_file} not found. Using default settings.')
            app_settings = DEFAULT_SETTINGS
        
        app = App(**app_settings)
        app.run()
    except Exception:
        logging.error(traceback.format_exc())
        # stop all parallel threads
        try:
            # stop all parallel threads
            app.should_stop.set()
        except UnboundLocalError:
            # if thread Event wasn't initialized yet
            pass
        # de-initialise pygame on error
        pygame_quit()


def print_profile():
    # print only the most time consuming calls
    p = pstats.Stats(path.join(filepath, '..', 'data', 'profile'))
    p.sort_stats(SortKey.TIME).print_stats(50)


if __name__ == '__main__':
    cProfile.run('main()', 
                 path.join(filepath, '..', 'data', 'profile'))
    print('\n')
    #print_profile()
