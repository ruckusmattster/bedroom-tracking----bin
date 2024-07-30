from machine import Pin, I2C
from ds1307 import DS1307
import time

# Initialize I2C for RTC
i2c = I2C(0, scl=Pin(5), sda=Pin(4))
rtc = DS1307(i2c)

# Initialize PIR sensors
pir_inside = Pin(15, Pin.IN)
pir_outside = Pin(14, Pin.IN)

# Log file to store entries and exits
log_file = "room_log.txt"

# Function to get current date and time from RTC
def get_current_datetime():
    year, month, day, weekday, hour, minute, second = rtc.datetime()
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(year, month, day, hour, minute, second)

# Function to log entry/exit
def log_event(event):
    timestamp = get_current_datetime()
    with open(log_file, 'a') as f:
        f.write(f"{timestamp} - {event}\n")

# Variables to track state
inside_active = False
outside_active = False

# Main loop
while True:
    inside_state = pir_inside.value()
    outside_state = pir_outside.value()
    
    if inside_state and not inside_active:
        inside_active = True
        if not outside_active:
            log_event("Entry")
        else:
            outside_active = False
            
    elif not inside_state and inside_active:
        inside_active = False
    
    if outside_state and not outside_active:
        outside_active = True
        if not inside_active:
            log_event("Exit")
        else:
            inside_active = False
            
    elif not outside_state and outside_active:
        outside_active = False

    time.sleep(0.1)
