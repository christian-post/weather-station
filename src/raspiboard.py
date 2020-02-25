import time
from datetime import datetime
import threading
from collections import deque
import logging
from statistics import mean, median

# raspberry pi modules in try:except for testing purpose on a PC
try:
    import board
    import adafruit_dht
    RPI = True
except ModuleNotFoundError as e:
    logging.error(e)
    RPI = False


class Logger:
    def __init__(self, app, read_interval, retry_delay=2):
        self.app = app
        #GPIO.setmode(GPIO.BCM)
        # specifiy the DHT device
        pin = self.app.settings['device_pin']
        self.device = adafruit_dht.DHT22(getattr(board, f'D{pin}'))
        # set the time between reads (ensure its >= 3)
        self.read_interval = max(3, read_interval)
        self.interval = 0
        self.repeated_readings = self.app.settings['repeated_readings']
        agggregation_methods = {
            'mean': mean,
            'median': median
            }
        self.aggregation = agggregation_methods[
                    self.app.settings['reading_aggregation']]
        # set the time between an unsuccessful read and the next read
        self.retry_delay = retry_delay
        # flag that determines which interval is used between reads
        self.read_successfull = False
        # set the belay for the main loop
        self.running_delay = 0.1
        # saves the time for calculating the delta time beween iterations
        self.prev_time = time.time()
        # storage deque for readings
        self.storage = deque()
        # task lists (scheduled actions)
        self.tasks = []
        # count the times a critical error occurred
        self.error_strikes = 0
        self.strike_threshold = 10
        # flag to determine if the pi is shutdown at the end
        self.initialise_shutdown = False


    def read_dht(self, delay=0):
        # thread that sends a request to the DHT11 device after some time
        time.sleep(delay)  # time waiting at the beginning of the thread
        while not self.app.should_stop.wait(self.interval):
            read_counter = 0
            temperature_values = []
            humidity_values = []
            while (read_counter < self.repeated_readings and
                   not self.app.should_stop.wait(self.retry_delay)):
                self.read_successfull = False
                try:
                    # Print the values to the logfile
                    temperature_values.append(self.device.temperature)
                    humidity_values.append(self.device.humidity)
                    logging.debug((f'{datetime.now().strftime("%H:%M:%S")}  ' +
                                   f'{self.device.temperature} C, ' +
                                   f'{round(self.device.humidity)} %'))
                    # indicate a successfull read and activate the green LED
                    read_counter += 1
                    self.read_successfull = True
                    # reset error count
                    self.error_strikes = 0
                except RuntimeError as error:
                    # check for critical errors
                    if ('Timed out waiting for PulseIn message' in error.args[0]
                        or 'DHT sensor not found, check wiring' in error.args[0]):
                        self.error_strikes += 1
                        logging.critical(error)
                    logging.warning(error.args[0])
                except Exception as e:
                    logging.error(e)
                # set the read interval depending on successful reading
                self.interval = (self.read_interval if self.read_successfull
                                 else self.retry_delay)
            # after repeated readings, aggregate 
            if read_counter >= 1:
                row = {
                        'temperature': self.aggregation(temperature_values),
                        'humidity': self.aggregation(humidity_values)
                        }
                # append data to the deque
                self.storage.append(row)


    def schedule_task(self, time, func):
        # TODO: make this an object instead of list?
        self.tasks.append([0, time, func])


    def mainloop(self):
        # start the thread that receives data from the dht device
        tk_thread = threading.Thread(target=lambda: self.read_dht())
        tk_thread.start()
        
        while not self.app.should_stop.wait(self.running_delay):
            # calculate how much time passed since the last iteration
            now = time.time()
            delta_time = now - self.prev_time
            self.prev_time = now

            # check for sensor readings
            if len(self.storage) > 0:
                row = self.storage.pop()
                self.app.indoor_data_heap.append(row)

            # check if too many errors occurred in a row
            if self.error_strikes >= self.strike_threshold:
                self.shutdown()

            for task in self.tasks:
                # advance the timer
                task[0] += self.running_delay
                # if timer > execution time
                if task[0] >= task[1]:
                    task[2]()

    def shutdown(self):
        logging.info('Program terminated')
        self.app.should_stop.set()
        self.initialise_shutdown = True