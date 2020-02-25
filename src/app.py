import pygame as pg
import pygame.freetype
import os
import json
import inspect
from itertools import cycle
import logging
import threading
from collections import deque

import clock
import states
from weather_api import get_weather_data, get_forecast_data
from functions import load_weather_codes
import raspiboard

pygame_error = pg.error
pygame_quit = pg.quit



class App:
    def __init__(self, **settings):
        pg.init()
        self.settings = settings
        self.screen = pg.display.set_mode((settings['window_width'],
                                           settings['window_height']))
        self.screen_rect = self.screen.get_rect()
        self.clock = pg.time.Clock()
        self.fps = settings['FPS']
        self.running = True
        self.should_stop = threading.Event()
        self.window_flags = 0
        self.mouse_visible = True

        self.daytime_clock = clock.Clock(self, fontsize=settings['clock_size'],
                                         fgcolor=pg.Color('White'))

        # load all assets
        self.base_dir = os.path.join(os.path.dirname(__file__), '..')
        assets_folder = os.path.join(self.base_dir, 'assets')
        data_folder = os.path.join(self.base_dir, 'data')
        # load font(s)
        font_file1 = os.path.join(assets_folder, 'digital-7 (mono).ttf')
        font_file2 = os.path.join(assets_folder, 'digital-7.ttf')
        self.fonts = {
            'digital_mono': pygame.freetype.Font(font_file1),
            'digital': pygame.freetype.Font(font_file2),
            'arial': pygame.freetype.SysFont('arial', size=32)
            }
        
        # load images
        sprite_files = list(
            filter(lambda x: x[-3:] == 'png', os.listdir(assets_folder)))
        sprite_images = {f[:-4]: pg.image.load(
            os.path.join(assets_folder, f)).convert_alpha()
                         for f in sprite_files}
        # construct the background image
        self.background_image = sprite_images['background']
        self.image = pg.Surface(self.background_image.get_size())
        self.image.fill(pg.Color(settings['background_color']))
        self.image.blit(self.background_image, (0, 0))
        # copy the image for redrawing
        self.image_original = self.image.copy()
        # list of rects where to update the screen
        self.update_rects = []

        with open(os.path.join(data_folder, 'api_key.txt'), 'r') as f:
            self.weather_api_key = f.read()

        self.city = settings['city']
        self.outdoor_data_heap = deque()
        self.forecast_data_heap = deque()
        self.indoor_data_heap = deque()

        if raspiboard.RPI:
            # if module runs on Pi
            self.logger = raspiboard.Logger(self,
                                            settings['indoor_read_interval'])
        else:
            # TODO: print "no logger connected" to screen
            pass

        # check if history.json exists and load it
        self.history_file = os.path.join(data_folder, 'history.json')
        if os.path.isfile(self.history_file):
            with open(self.history_file, 'r') as f:
                self.history = json.load(f)
        else:
            self.history = {
                'outdoor_timestamp': [],
                'outdoor_temperature': [],
                'outdoor_humidity': [],
                'outdoor_weather': [],
                'indoor_timestamp': [],
                'indoor_temperature': [],
                'indoor_humidity': []
            }
        self.weather_codes = load_weather_codes(os.path.join(data_folder,
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

        # setup the State Machine
        self.state_dict = {}
        self.state_name = 'Main'  # state at the start
        self.state = None
        self.setup_states()
        self.state.redraw()
        
        # what plot to show in the Plots state
        self.show_plot = 'outdoor_temperature'

        # call API once in the beginning
        t1 = threading.Thread(target=self.process_weather_beginning())
        t1.start()

        # mirror the event queue
        self.event_queue = []

        # for debugging
        self.debug = bool(settings['debug_mode'])
        if self.debug:
            self.states_cycle = cycle(self.state_dict.keys())
            next(self.states_cycle)


    def events(self):
        self.event_queue = []
        for event in pg.event.get():
            self.event_queue.append(event)
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
                elif event.key == pg.K_s:
                    if self.debug:
                        # TODO: for debugging
                        # cycle the states
                        self.state.next = next(self.states_cycle)
                        self.state.done = True
            elif event.type == pg.MOUSEBUTTONDOWN:
                if self.settings['log_mouse_position']:
                    mpos = pg.mouse.get_pos()
                    logging.info(f'mouse {int(mpos[0])},{int(mpos[1])}')


    def update(self, dt):
        if self.state.done:
            self.flip_state()
        self.state.update(dt)

        pg.display.set_caption(f'{round(self.clock.get_fps(), 1)}')


    def draw(self):
        self.state.draw(self.screen)


    def setup_states(self):
        # get a dictionary with all classes from the 'states' module
        self.state_dict = dict(inspect.getmembers(states, inspect.isclass))
        for key, state in self.state_dict.items():
            self.state_dict[key] = state(self)
        # remove the parent state class
        del self.state_dict['State']
        # define the state at the start of the program
        self.state = self.state_dict[self.state_name]
        # set a states name for __repr__
        for name, state in self.state_dict.items():
            state.name = name
        self.state.startup()


    def flip_state(self):
        '''set the state to the next if the current state is done'''
        self.state.done = False
        # set the current and next state to the previous and current state
        previous, self.state_name = self.state_name, self.state.next
        self.state.cleanup()
        if self.state_name is None:
            self.running = False
        else:
            self.state = self.state_dict[self.state_name]
            self.state.startup()
            self.state.previous = previous


    def reset_app_screen(self):
        self.screen = pg.display.set_mode((
            self.settings['window_width'],
            self.settings['window_height']
        ), self.window_flags)
        self.screen_rect = self.screen.get_rect()
        self.state.redraw()


    def process_weather_beginning(self):
        # get the current weather
        outdoor_data = get_weather_data(self.weather_api_key,
                                        self.city)
        self.outdoor_data_heap.append(outdoor_data)
        # get the 3 hourly weather forecast
        forecast_data = get_forecast_data(self.weather_api_key,
                                          self.city)
        self.forecast_data_heap.append(forecast_data)
        # update the screen after receiving information
        self.state.redraw()
        

    def process_outdoor_weather(self):
        while not self.should_stop.wait(self.settings['api_interval_weather']):
            # get the current weather
            outdoor_data = get_weather_data(self.weather_api_key,
                                            self.city)
            self.outdoor_data_heap.append(outdoor_data)


    def process_weather_forecast(self):
        while not self.should_stop.wait(
                self.settings['api_interval_forecast']):
            # get the 3 hourly weather forecast
            forecast_data = get_forecast_data(self.weather_api_key,
                                              self.city)
            self.forecast_data_heap.append(forecast_data)
    
    
    def start_threads(self):
        t1 = threading.Thread(target=self.process_outdoor_weather)
        t1.start()
        t2 = threading.Thread(target=self.process_weather_forecast)
        t2.start()
        if raspiboard.RPI:
            t3 = threading.Thread(target=self.logger.mainloop)
            t3.start()


    def quit(self):
        # TODO: save settings etc
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f)
        # stop parallel threads
        self.should_stop.set()
        pg.quit()


    def run(self):
        self.start_threads()
        while self.running:
            dt = self.clock.tick(self.fps) / 1000
            self.events()
            self.update(dt)
            self.draw()
        self.quit()
