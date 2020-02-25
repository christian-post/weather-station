import datetime
import pygame as pg
import logging

import clock
import functions as func


class State(object):
    def __init__(self, app):
        self.app = app
        self.next = None  # what comes after if this is done
        self.done = False  # if true, the next state gets executed
        self.previous = None  # the state that was executed before

        if not hasattr(self, 'name'):
            self.name = 'State'

    def __repr__(self):
        return self.name

    def startup(self):
        pass

    def cleanup(self):
        pass

    def get_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self):
        pass


class Main(State):
    """
    This is the default state that shows indoor and outdoor temperature
    as well as the weather forecast
    """
    def __init__(self, app):
        State.__init__(self, app)
        self.next = 'Plots'
        
        self.outdoor_data = {
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
        self.forecast_data = {
            'list': []
            }
        
        self.indoor_data = {
            'temperature': 88.8,
            'humidity': 88
            }
    
        # user interface elements
        self.ui_elements = pg.sprite.Group()
        func.UI_Button(self, image=None, 
                       rect=pg.Rect(0, 0, 160, 160),
                       position=(140, 120), anchor='center',
                       callback=self.switch_to_plots, 
                       callback_kwargs={'plot': 'outdoor_temperature'})
        func.UI_Button(self, image=None, 
                       rect=pg.Rect(0, 0, 160, 160),
                       position=(140, 320), anchor='center',
                       callback=self.switch_to_plots, 
                       callback_kwargs={'plot': 'outdoor_humidity'})

    def startup(self):
        # switch to normal FPS mode
        self.app.fps = self.app.settings['FPS']
        self.redraw()

    def update(self, dt):
        # update the clock (system time, timer events etc
        self.app.daytime_clock.update(dt, show_seconds=False)
        
        # check for data from api
        if len(self.app.outdoor_data_heap) >= 1:
            data = self.app.outdoor_data_heap.pop()
            self.outdoor_data = data

            time = clock.get_timestamp()
            temp = func.celsius(data['main'].get('temp', None))
            humidity = data['main'].get('humidity', None)
            logging.debug((time, temp))
            weather = data['weather'][0]
            self.app.history['outdoor_timestamp'].append(time)
            self.app.history['outdoor_temperature'].append(temp)
            self.app.history['outdoor_humidity'].append(humidity)
            self.app.history['outdoor_weather'].append(weather)
            self.redraw()
            
        if len(self.app.forecast_data_heap) >= 1:
            data = self.app.forecast_data_heap.pop()
            self.forecast_data = data
            self.redraw()

        if len(self.app.indoor_data_heap) >= 1:
            self.indoor_data = self.app.indoor_data_heap.pop()
            self.app.history['indoor_timestamp'].append(
                                clock.get_timestamp())
            self.app.history['indoor_temperature'].append(
                            self.indoor_data['temperature'])
            self.app.history['indoor_humidity'].append(
                            self.indoor_data['humidity'])
            self.redraw()
        
        # UI elements
        mpos = pg.mouse.get_pos()
        mouse_pressed = False
        for event in self.app.event_queue:
            if event.type == pg.MOUSEBUTTONDOWN:
                mouse_pressed = True
        for elem in self.ui_elements:
            elem.update(mpos, mouse_pressed)

    def draw(self, screen):
        screen_rect = self.app.screen_rect
        screen.blit(self.app.image, screen_rect)
        # draw the time and date
        # TODO: only draw clock when updated?
        self.app.daytime_clock.draw(screen,
                                (screen_rect.centerx,
                                 screen_rect.h - 120),
                                'center')
        self.app.update_rects.append(self.app.daytime_clock.rect.inflate(
            self.app.daytime_clock.rect.w * 1.5,
            self.app.daytime_clock.rect.h * 1.5))
        day = clock.get_weekday()
        date_string = f'{day[0][:3]}  {day[1]:02d}.{day[2]:02d}.{day[3]}'
        date_txt, date_rect = self.app.fonts['digital_mono'].render(
                    date_string, fgcolor=pg.Color('white'), size=36)
        date_rect.center = (screen_rect.centerx,
                            screen_rect.h - 50)
        self.app.update_rects.append(date_rect)
        screen.blit(date_txt, date_rect)
        
        for elem in self.ui_elements:
            elem.draw(screen)
            self.app.update_rects.append(elem.rect)
            if self.app.debug:
                pg.draw.rect(screen, pg.Color('red'), elem.rect, 1)

        pg.display.update(self.app.update_rects)
        # TODO: update_rects as property of state?
        self.app.update_rects = []
                


    def redraw(self):
        # draw the temperatures and humidity
        # TODO: Add temperature to forecast
        # TODO: image as property of state?
        screen_rect = self.app.screen.get_rect()

        render_positions = [
            {
                'txt': 'OUTDOOR',
                'size': 48,
                'pos': (136, 48),
                'anchor': 'center',
                'font': 'digital_mono'
            },
            {
                'txt': 'INDOOR',
                'size': 48,
                'pos': (screen_rect.w - 136, 48),
                'anchor': 'center',
                'font': 'digital_mono'
                
            },
            # outdoor temp. before decimal
            {
                'txt': func.format_temperature(
                    self.outdoor_data['main'].get("temp", "-.-"))[0],
                'size': 136,
                'pos': (160, 166),
                'anchor': 'bottomright',
                'font': 'digital_mono'
            },
            # outdoor temp. after decimal
            {
                'txt': func.format_temperature(
                    self.outdoor_data['main'].get("temp", "-.-"))[1],
                'size': 80,
                'pos': (200, 166),
                'anchor': 'midbottom',
                'font': 'digital_mono'
            },
            # indoor temperature before decimal
            {
                'txt': f'{int(self.indoor_data["temperature"])}',
                'size': 136,
                'pos': (screen_rect.w - 108, 168),
                'anchor': 'bottomright',
                'font': 'digital_mono'
            },
            # indoor temperature after decimal
            {
                'txt': f'{func.first_decimal(self.indoor_data["temperature"])}',
                'size': 80,
                'pos': (screen_rect.w - 64, 168),
                'anchor': 'midbottom',
                'font': 'digital_mono'
            },
            {
                'txt': 'TEMPERATURE',
                'size': 32,
                'pos': (136, 196),
                'anchor': 'center',
                'font': 'digital_mono'
            },
            {
                'txt': 'TEMPERATURE',
                'size': 32,
                'pos': (screen_rect.w - 136, 196),
                'anchor': 'center',
                'font': 'digital_mono'
            },
            {
                'txt': f'{self.outdoor_data["main"].get("humidity", "--")}',
                'size': 136,
                'pos': (160, 338),
                'anchor': 'bottomright',
                'font': 'digital_mono'
            },
            {
                'txt': f'{int(self.indoor_data["humidity"])}',
                'size': 136,
                'pos': (screen_rect.w - 108, 338),
                'anchor': 'bottomright',
                'font': 'digital_mono'
            },
            {
                'txt': 'HUMIDITY',
                'size': 32,
                'pos': (136, 366),
                'anchor': 'center',
                'font': 'digital_mono'
            },
            {
                'txt': 'HUMIDITY',
                'size': 32,
                'pos': (screen_rect.w - 136, 366),
                'anchor': 'center',
                'font': 'digital_mono'
            },
        ]
        self.app.image.blit(self.app.image_original, (0, 0))
        self.app.update_rects.append(screen_rect)
        for item in render_positions:
            font = self.app.fonts[item['font']]
            txt, rect = font.render(item['txt'],
                                    fgcolor=pg.Color('white'),
                                    size=item['size'])
            # set the rect's position
            setattr(rect, item['anchor'], item['pos'])
            self.app.image.blit(txt, rect)

        # draw the current weather condition
        try:
            code = self.app.history['outdoor_weather'][-1]['icon'] + '.png'
            image = self.app.weather_code_surfaces.get(code, None)
        except IndexError:
            image = None
        if image:
            image = pg.transform.scale(image, (128, 128))
            rect = image.get_rect()
            rect.center = (screen_rect.centerx,
                           screen_rect.h * 0.16)
            self.app.image.blit(image, rect)

        # draw the 3 hourly forecast
        for i, item in enumerate(self.forecast_data['list'][:6]):
            code = item['weather'][0]['icon'] + '.png'
            image = self.app.weather_code_surfaces.get(code, None)
            x_coord = (screen_rect.centerx - 100) + 42 * i
            if image:
                rect = image.get_rect()
                rect.center = (x_coord, screen_rect.h * 0.36)
                self.app.image.blit(image, rect)

            timestamp = datetime.datetime.utcfromtimestamp(item['dt'])
            time = timestamp.strftime('%H:%M')
            txt, rect = self.app.fonts['digital'].render(time, fgcolor=pg.Color('white'),
                                             size=16)
            rect.center = (x_coord, screen_rect.h * 0.42 + 32)
            self.app.image.blit(txt, rect)

            temperature = func.celsius(item['main']['temp'])
            txt, rect = self.app.fonts['digital'].render(f'{round(temperature)}',
                                             fgcolor=pg.Color('white'),
                                             size=24)
            rect.center = (x_coord, screen_rect.h * 0.37 + 32)
            self.app.image.blit(txt, rect)

        # draw the city name
        try:
            city_name = func.replace_umlauts(
                    self.forecast_data['city']['name'] +
                    ', ' +
                    self.forecast_data['city']['country'])
        except KeyError:
            city_name = 'Could not connect'
        txt, rect = self.app.fonts['digital'].render(city_name,
                                         fgcolor=pg.Color('white'),
                                         size=36)
        rect.center = (screen_rect.centerx, screen_rect.h * 0.58)
        self.app.image.blit(txt, rect)
        
    def switch_to_plots(self, plot):
        self.app.state.next = 'Plots'
        self.app.show_plot = plot
        self.app.state.done = True


class Plots(State):
    """
    this state shows the developments of past outdoor temperature and humidity
    as graphs
    """
    def __init__(self, app):
        State.__init__(self, app)
        self.next = 'Main'

        self.background = pg.Surface(self.app.screen_rect.size)
        self.background.fill(
            pg.Color(self.app.settings['background_color']))
        self.image = pg.Surface(self.app.screen_rect.size)
        self.rect = self.image.get_rect()
        self.plot_rect = self.rect.copy()  # gets changed on startup

        self.data = {}
        self.points_to_draw = []
        # these values are calculated on startup
        self.plot_width = 0
        self.plot_height = 0
        self.margin_x = 0
        self.margin_y = 0
        self.max_y = 30  # default value
        self.min_y = 0
        self.max_x = 10  # default value
        self.min_x = 0
        self.tickmark_len = 5
        self.axis_label_fontsize = 18
        self.title_fontsize = 36
        self.button_fontsize = 36
        self.axis_thickness = 2
        self.plot_thickness = 4
        self.timer = 0
        self.drawing_index = 0
        self.animation_delay = 0.05
        self.animation_done = False
        self.title = '---'

        # formatting
        # TODO: take these as hex values from settings file
        self.colors = {
            'axis': pg.Color('white'),
            'plot': pg.Color('white')
        }
        
        # create some buttons for navigation
        self.ui_elements = pg.sprite.Group()
        txt, rect = self.app.fonts['digital'].render(text='Back',
                                             fgcolor=self.colors['axis'],
                                             size=self.button_fontsize)
        func.UI_Button(self, image=txt, rect=rect,
                       position=(self.app.settings['window_width'] - 64, 320),
                       anchor='center',
                       callback=self.exit)

    def startup(self):
        # adjust FPS to make the display smoother
        self.app.fps = self.app.settings['FPS_plot_mode']
        # create plot data from history
        self.data['y'] = []
        y_array = self.app.history[self.app.show_plot]
        self.title = self.app.show_plot.replace('_',' ').title()
        if 'humidity' in self.app.show_plot:
            self.max_y = 100
            self.min_y = 0
        else:
            self.max_y = max(y_array) + 5
            self.min_y = min(y_array) - 5
        self.max_x = len(y_array) + 1
        self.min_x = 0
        self.plot_width = int(self.app.settings['window_width'] * 0.75)
        self.plot_height = int(self.app.settings['window_height'] * 0.75)
        self.margin_x = int((self.app.settings['window_width']
                             - self.plot_width) / 2) - 24
        self.margin_y = int((self.app.settings['window_height']
                             - self.plot_height) / 2)
        self.plot_rect = pg.Rect(self.margin_x, self.margin_y, 
                                 self.plot_width, self.plot_height)

        for x, y in enumerate(y_array):
            plot_y = (self.plot_height -
                      ((y / self.max_y) * self.plot_height) + self.margin_y)
            plot_x = x * (self.plot_width / len(y_array)) + self.margin_x
            self.data['y'].append((plot_x, plot_y))

        self.redraw()

    def cleanup(self):
        self.points_to_draw = []
        self.drawing_index = 0
        self.animation_done = False

    def update(self, dt):
        mpos = pg.mouse.get_pos()
        mouse_pressed = False
        for event in self.app.event_queue:
            if event.type == pg.MOUSEBUTTONDOWN:
                mouse_pressed = True
        for elem in self.ui_elements:
            elem.update(mpos, mouse_pressed)
            
        if not self.animation_done:
            self.timer += dt
            if self.timer >= self.animation_delay:
                self.timer = 0
                for i in range(5):
                    # add 5 points at once
                    self.points_to_draw.append(
                        self.data['y'][self.drawing_index]
                    )
                    self.drawing_index += 1
                    if self.drawing_index >= len(
                            self.data['y']) - 1:
                        self.animation_done = True
                        break
                self.redraw()

    def draw(self, screen):
        screen.blit(self.image, self.rect)
        self.app.update_rects.append(self.rect)
        
        for elem in self.ui_elements:
            elem.draw(screen)
            self.app.update_rects.append(elem.rect)
            if self.app.debug:
                pg.draw.rect(screen, pg.Color('red'), elem.rect, 1)
        
        if self.app.debug:
            pg.draw.rect(screen, pg.Color('red'), self.plot_rect, 1)

        pg.display.update(self.app.update_rects)
        # TODO: update_rects as property of state?
        self.app.update_rects = []

    def redraw(self):
        # draw some lines as a test
        self.image.blit(self.background, (0, 0))
        # draw the title
        txt, rect = self.app.fonts['digital'].render(text=self.title,
                                             fgcolor=self.colors['axis'],
                                             size=self.title_fontsize)
        rect.centerx = self.rect.centerx
        rect.bottom = self.plot_rect.top - 4
        self.image.blit(txt, rect)
        # draw the axes
        # x axis
        pg.draw.line(self.image, self.colors['axis'],
                     self.plot_rect.bottomleft,
                     self.plot_rect.bottomright,
                     self.axis_thickness)
        # x tickmarks and labels
        no_of_ticks = self.max_x
        for x in range(no_of_ticks + 1):
            tick_pos_x = x * (self.plot_width / no_of_ticks) + self.margin_x
            pg.draw.line(self.image, self.colors['axis'],
                         (tick_pos_x, self.rect.h - self.margin_y),
                         (tick_pos_x, self.rect.h - self.margin_y
                          + self.tickmark_len))
            if x % 5 == 0:
                # TODO: make this value "5" dependent on the len of the array
                txt, rect = self.app.fonts['digital'].render(text=str(x),
                                                 fgcolor=self.colors['axis'],
                                                 size=self.axis_label_fontsize)
                rect.midtop = (tick_pos_x, self.rect.h - self.margin_y
                               + self.tickmark_len + 5)
                self.image.blit(txt, rect)
        # y axis
        pg.draw.line(self.image, self.colors['axis'],
                     self.plot_rect.bottomleft,
                     self.plot_rect.topleft,
                     self.axis_thickness)
        # y tickmarks and labels
        no_of_ticks = int(self.max_y - self.min_y)
        for y in range(no_of_ticks + 1):
            tick_pos_y = y * (self.plot_height / no_of_ticks) + self.margin_y
            pg.draw.line(self.image, self.colors['axis'],
                         (self.margin_x - self.tickmark_len, tick_pos_y),
                         (self.margin_x, tick_pos_y))
            if y % self.app.settings['plot_ytick_intervals'][self.app.show_plot] == 0:
                number = str(int(no_of_ticks - y + self.min_y))
                txt, rect = self.app.fonts['digital'].render(text=number,
                                                 fgcolor=self.colors['axis'],
                                                 size=self.axis_label_fontsize)
                rect.midright = (self.margin_x - self.tickmark_len - 5, tick_pos_y)
                self.image.blit(txt, rect)
        # draw the plot
        if len(self.points_to_draw) > 1:
            pg.draw.lines(self.image, self.colors['plot'], False,
                          self.points_to_draw, self.plot_thickness)
    
    def exit(self):
        self.done = True
