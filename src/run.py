import traceback
from app import App, pygame_error, pygame_quit


if __name__ == '__main__':
    app_settings = {
        'window_width': 800,
        'window_height': 480,
        'background_color': '#075869',
        'FPS': 10,
        'clock_size': 96,
        'api_interval_weather': 300,
        'api_interval_forecast': 600,
        'city': 'Osnabrück,DE'
    }
    try:
        app = App(**app_settings)
        app.run()
    except pygame_error:
        traceback.print_exc()
        pygame_quit()

