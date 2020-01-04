import pygame as pg
import pygame.freetype
import os
import json
import csv
import datetime

import clock
from weather_api import get_weather_data, get_forecast_data

pygame_error = pg.error
pygame_quit = pg.quit


def celsius(kelvin):
    return kelvin - 273.15


def replace_umlauts(string):
    umlauts = {
        'ä': 'ae',
        'ö': 'oe',
        'ü': 'ue',
        'ß': 'ss'
    }
    for key, value in umlauts.items():
        string = string.replace(key, value)
    return string


def load_weather_codes(filename):
    codes = {}
    with open(filename) as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=',')
        for i, row in enumerate(csv_reader):
            codes[row['ID']] = row
    return codes


class App:
    def __init__(self, **settings):
        pg.init()
        self.settings = settings
        self.screen = pg.display.set_mode((
            settings['window_width'],
            settings['window_height']
        )
        )
        self.screen_rect = self.screen.get_rect()
        self.clock = pg.time.Clock()
        self.fps = settings['FPS']
        self.running = True
        self.window_flags = 0
        self.mouse_visible = True

        self.daytime_clock = clock.Clock(self, fontsize=settings['clock_size'],
                                         fgcolor=pg.Color('White'))

        # load all assets
        self.base_dir = os.path.join(os.path.dirname(__file__), '..')
        assets_folder = os.path.join(self.base_dir, 'assets')
        # load font(s)
        font_file = os.path.join(assets_folder, 'digital-7.ttf')
        self.font = pygame.freetype.Font(font_file, size=36)
        # load images
        sprite_files = list(
            filter(lambda x: x[-3:] == 'png', os.listdir(assets_folder)))
        sprite_images = {f[:-4]: pg.image.load(
            os.path.join(assets_folder, f)).convert_alpha()
                         for f in sprite_files}
        # construct the background image
        self.background_image = sprite_images['background_mockup']
        self.image = pg.Surface(self.background_image.get_size())
        self.image.fill(pg.Color(settings['background_color']))
        self.image.blit(self.background_image, (0, 0))

        with open(os.path.join(assets_folder, 'api_key.txt'), 'r') as f:
            self.weather_api_key = f.read()

        self.city = settings['city']
        self.outdoor_data = get_weather_data(self.weather_api_key,
                                             self.city)
        self.forecast_data = get_forecast_data(self.weather_api_key,
                                               self.city)
        # set api call interval in seconds
        self.daytime_clock.add_timer('weather_outdoor',
                                     settings['api_interval_weather'],
                                     self.process_outdoor_weather)
        self.daytime_clock.add_timer('weather_forecast',
                                     settings['api_interval_forecast'],
                                     self.process_weather_forecast)
        self.history = {
            'outdoor_timestamp': [],
            'outdoor_temperature': [],
            'outdoor_humidity': [],
            'outdoor_weather': []
        }
        self.weather_codes = load_weather_codes(os.path.join(assets_folder,
                                                'condition_codes.csv'))
        # load the corresponding images
        # get unique weather codes
        weather_image_names = []
        for condition in self.weather_codes.values():
            icon_day = condition['Icon_day'] + '.png'
            icon_night = icon_day.replace('d', 'n')
            for icon in [icon_day, icon_night]:
                if icon not in weather_image_names:
                    weather_image_names.append(icon)

        self.weather_code_surfaces = {}
        for filename in weather_image_names:
            image = pg.image.load(os.path.join(assets_folder,
                                               filename)).convert_alpha()
            self.weather_code_surfaces[filename] = image

        # call API once in the beginning
        self.process_weather_forecast()
        self.process_outdoor_weather()

    def events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.KEYDOWN:
                if (event.key == pg.K_RETURN
                        and pg.key.get_pressed()[pg.K_LALT]):
                    # toggle fullscreen
                    self.window_flags = self.window_flags ^ pg.FULLSCREEN
                    self.mouse_visible = not self.mouse_visible
                    pg.mouse.set_visible(self.mouse_visible)
                    self.reset_app_screen()
                elif (event.key == pg.K_ESCAPE
                      and self.window_flags & pg.FULLSCREEN == pg.FULLSCREEN):
                    # exit fullscreen
                    self.window_flags = self.window_flags & ~pg.FULLSCREEN
                    self.mouse_visible = True
                    pg.mouse.set_visible(True)
                    self.reset_app_screen()

    def update(self, dt):
        # get system time
        self.daytime_clock.update(dt, show_seconds=False)

        for event, callback in self.daytime_clock.clear_timer_events().items():
            print(f'called {event} at {datetime.datetime.now()}')
            if callback:
                callback()

    def draw(self):
        self.screen.blit(self.image, self.screen_rect)
        # draw the time and date
        self.daytime_clock.draw(self.screen,
                                (self.screen_rect.centerx,
                                 self.screen_rect.h - 120),
                                'center')
        day = clock.get_weekday()
        date_string = f'{day[0][:3]}  {day[1]:02d}.{day[2]:02d}.{day[3]}'
        date_txt, date_rect = self.font.render(date_string,
                                               fgcolor=pg.Color('white'),
                                               size=36
                                               )
        date_rect.center = (self.screen_rect.centerx,
                            self.screen_rect.h - 50)
        self.screen.blit(date_txt, date_rect)

        # draw the temperatures and humidity
        # TODO: render once, not every frame!
        # TODO: put this in a dict with text, position and render in a loop!
        # TODO: Add temperature to forecast
        txt, rect = self.font.render('OUTDOOR',
                                     fgcolor=pg.Color('white'),
                                     size=48)
        rect.center = (136, 48)
        self.screen.blit(txt, rect)

        txt, rect = self.font.render('INDOOR',
                                     fgcolor=pg.Color('white'),
                                     size=48)
        rect.center = (self.screen_rect.w - 136, 48)
        self.screen.blit(txt, rect)
        # temperature value
        temp = f'{celsius(self.outdoor_data["main"]["temp"]):.1f} C'
        txt, rect = self.font.render(temp,
                                     fgcolor=pg.Color('white'),
                                     size=110)
        rect.center = (140, 130)
        self.screen.blit(txt, rect)

        temp = '18.0 C'
        txt, rect = self.font.render(temp,
                                     fgcolor=pg.Color('white'),
                                     size=110)
        rect.center = (self.screen_rect.w - 130, 130)
        self.screen.blit(txt, rect)

        txt, rect = self.font.render('temperature',
                                     fgcolor=pg.Color('white'),
                                     size=32)
        rect.center = (136, 196)
        self.screen.blit(txt, rect)
        rect.center = (self.screen_rect.w - 136, 196)
        self.screen.blit(txt, rect)

        # draw the humidity
        humidity = self.outdoor_data.get('main').get('humidity')
        hum_string = f'{humidity} %'
        txt, rect = self.font.render(hum_string,
                                     fgcolor=pg.Color('white'),
                                     size=110)
        rect.center = (140, 300)
        self.screen.blit(txt, rect)

        #humidity = self.outdoor_data.get('main').get('humidity')
        hum_string = '50 %'
        txt, rect = self.font.render(hum_string,
                                     fgcolor=pg.Color('white'),
                                     size=110)
        rect.center = (self.screen_rect.w - 130, 300)
        self.screen.blit(txt, rect)

        txt, rect = self.font.render('humidity',
                                     fgcolor=pg.Color('white'),
                                     size=32)
        rect.center = (136, 366)
        self.screen.blit(txt, rect)
        rect.center = (self.screen_rect.w - 136, 366)
        self.screen.blit(txt, rect)

        # draw the weather conditions
        city_name = replace_umlauts(self.outdoor_data['name'])
        txt, rect = self.font.render(city_name,
                                     fgcolor=pg.Color('white'),
                                     size=36)
        rect.center = (self.screen_rect.centerx, self.screen_rect.h * 0.55)
        self.screen.blit(txt, rect)
        code = self.history['outdoor_weather'][-1]['icon'] + '.png'
        image = self.weather_code_surfaces.get(code, None)
        if image:
            image = pg.transform.scale(image, (128, 128))
            rect = image.get_rect()
            rect.center = (self.screen_rect.centerx,
                           self.screen_rect.h * 0.2)
            self.screen.blit(image, rect)
        # draw the 3 hourly forecast
        for i, item in enumerate(self.forecast_data['list'][:6]):
            code = item['weather'][0]['icon'] + '.png'
            image = self.weather_code_surfaces.get(code, None)
            if image:
                rect = image.get_rect()
                x_coord = (self.screen_rect.centerx - 100) + 42 * i
                rect.center = (x_coord, self.screen_rect.h * 0.4)
                self.screen.blit(image, rect)
            timestamp = datetime.datetime.utcfromtimestamp(item['dt'])
            time = timestamp.strftime('%H:%M')
            txt, rect = self.font.render(time, fgcolor=pg.Color('white'),
                                         size=16)
            rect.center = (x_coord, self.screen_rect.h * 0.4 + 32)
            self.screen.blit(txt, rect)


        pg.display.update()

    def reset_app_screen(self):
        self.screen = pg.display.set_mode((
            self.settings['window_width'],
            self.settings['window_height']
        ), self.window_flags)
        self.screen_rect = self.screen.get_rect()
        pg.display.update()

    def process_outdoor_weather(self):
        # get the current weather
        self.outdoor_data = get_weather_data(self.weather_api_key,
                                             self.city)
        time = clock.get_timestamp()
        temp = celsius(self.outdoor_data['main']['temp'])
        humidity = self.outdoor_data['main']['humidity']
        weather = self.outdoor_data['weather'][0]
        self.history['outdoor_timestamp'].append(time)
        self.history['outdoor_temperature'].append(temp)
        self.history['outdoor_humidity'].append(humidity)
        self.history['outdoor_weather'].append(weather)

    def process_weather_forecast(self):
        # get the 3 hourly weather forecast
        self.forecast_data = get_forecast_data(self.weather_api_key,
                                               self.city)
        print(datetime.datetime.now())
        print('Forecast for the next 24 hours:')
        for item in self.forecast_data['list'][:8]:
            timestamp = datetime.datetime.utcfromtimestamp(item['dt'])
            condition = item['weather'][0]['description']
            rain = item.get('rain', None)
            string = (f'{timestamp.strftime("%a %d.%m.%y %H:%M")} '
                      f'{condition.capitalize()}')
            if rain:
                string += f', {rain["3h"]} mm'
            print(string)

    def quit(self):
        # TODO: save settings etc
        with open(os.path.join(self.base_dir, 'history.json'), 'w') as f:
            json.dump(self.history, f)
        pg.quit()

    def run(self):
        while self.running:
            dt = self.clock.tick(self.fps) / 1000
            self.events()
            self.update(dt)
            self.draw()
        self.quit()
