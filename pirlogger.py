import network
import socket
import time
from machine import Pin, I2C
from ds1307 import DS1307
from wifi_config import SSID, PASSWORD
import json
from collections import defaultdict
import _thread

# Connect to WiFi
def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    
    while not wlan.isconnected():
        pass
    
    print('Connected to WiFi')
    print(wlan.ifconfig())

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
daily_entries = 0
daily_exits = 0
total_entries = 0
total_exits = 0
entries_per_hour = defaultdict(int)

# Connect to WiFi
connect_to_wifi()

# Main loop
def main():
    global daily_entries, daily_exits, total_entries, total_exits, entries_per_hour
    
    while True:
        inside_state = pir_inside.value()
        outside_state = pir_outside.value()
        
        current_datetime = get_current_datetime()
        current_date, current_time = current_datetime.split(' ')
        current_hour = int(current_time.split(':')[0])
        
        if inside_state and not inside_active:
            inside_active = True
            if not outside_active:
                log_event("Entry")
                daily_entries += 1
                total_entries += 1
                entries_per_hour[current_hour] += 1
            else:
                outside_active = False
                
        elif not inside_state and inside_active:
            inside_active = False
        
        if outside_state and not outside_active:
            outside_active = True
            if not inside_active:
                log_event("Exit")
                daily_exits += 1
                total_exits += 1
            else:
                inside_active = False
                
        elif not outside_state and outside_active:
            outside_active = False
        
        time.sleep(0.1)

# Function to create HTML content
def generate_webpage():
    global daily_entries, daily_exits, total_entries, total_exits, entries_per_hour
    
    daily_average_entries = total_entries / (len(entries_per_hour) or 1)
    daily_average_exits = total_exits / (len(entries_per_hour) or 1)
    
    entries_per_hour_list = sorted(entries_per_hour.items())
    hours = [str(hour) for hour, _ in entries_per_hour_list]
    entries = [count for _, count in entries_per_hour_list]
    cumulative_entries = [sum(entries[:i+1]) for i in range(len(entries))]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Room Entry/Exit Log</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #2E8B57;
                color: #FFFFFF;
                text-align: center;
                margin: 0;
                padding: 0;
            }}
            header {{
                padding: 20px;
                background-color: #006400;
            }}
            .counter {{
                display: inline-block;
                margin: 20px;
                font-size: 24px;
            }}
            .counter span {{
                font-style: italic;
            }}
            .chart-container {{
                width: 90%;
                max-width: 600px;
                margin: 20px auto;
            }}
            canvas {{
                background-color: #FFFFFF;
            }}
            @media (min-width: 768px) {{
                .chart-container {{
                    width: 45%;
                    display: inline-block;
                }}
            }}
        </style>
    </head>
    <body>
        <header>
            <div class="counter">
                Entries Today: {daily_entries} <br><span>Daily Average: {daily_average_entries:.2f}</span>
            </div>
            <div class="counter">
                Exits Today: {daily_exits} <br><span>Daily Average: {daily_average_exits:.2f}</span>
            </div>
        </header>
        <div class="chart-container">
            <h2>Entries Per Hour</h2>
            <canvas id="entriesChart"></canvas>
        </div>
        <div class="chart-container">
            <h2>Cumulative Entries</h2>
            <canvas id="cumulativeChart"></canvas>
        </div>
        <script>
            var ctx1 = document.getElementById('entriesChart').getContext('2d');
            var entriesChart = new Chart(ctx1, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(hours)},
                    datasets: [{{
                        label: 'Entries Per Hour',
                        data: {json.dumps(entries)},
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        fill: true
                    }}]
                }},
                options: {{
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});

            var ctx2 = document.getElementById('cumulativeChart').getContext('2d');
            var cumulativeChart = new Chart(ctx2, {{
                type: 'line',
                data: {{
                    labels: {json.dumps(hours)},
                    datasets: [{{
                        label: 'Cumulative Entries',
                        data: {json.dumps(cumulative_entries)},
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        fill: true
                    }}]
                }},
                options: {{
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html

# Start the web server
def start_web_server():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print('Listening on', addr)

    while True:
        cl, addr = s.accept()
        print('Client connected from', addr)
        request = cl.recv(1024)
        request = str(request)

        response = generate_webpage()
        cl.send('HTTP/1.1 200 OK\r\n')
        cl.send('Content-Type: text/html\r\n')
        cl.send('Connection: close\r\n\r\n')
        cl.sendall(response)
        cl.close()

# Run main and web server in parallel
_thread.start_new_thread(main, ())
start_web_server()
