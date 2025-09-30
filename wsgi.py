"""
Copyright (C) 2025 Julian Metzler

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import json
import threading
import time

from flask import Flask, request, Response
from homeassistant_api import Client
from pyfis.mobitec import MobitecMatrix

from secrets import *


app = Flask(__name__)


NOTIFICATION_DURATION_SECONDS = 2 * 60 * 60
CYCLE_TIME_SECONDS = 3


class NotificationDisplay:
    def __init__(self, port, address, home_assistant):
        self.display = MobitecMatrix(port, address)
        self.hass = home_assistant
        self.running = True
        self.display_on = True
        self.notifications = []

    def notify(self, text):
        self.notifications.append((time.time(), text))
        self.notifications.sort(key=lambda n:n[0], reverse=True) # newest first
        self.update_display()

    def get_state(self):
        return self.display_on

    def set_state(self, state):
        self.display_on = state
        self.update_display()

    def get_default_screen_text(self):
        # Build text for default screen out of sensor values
        co2_state = self.hass.get_state(entity_id="sensor.co2_meter_co2")
        pm25_state = self.hass.get_state(entity_id="sensor.flur_luft_pm25")
        voc_state = self.hass.get_state(entity_id="sensor.flur_luft_voc_index")
        rh_state = self.hass.get_state(entity_id="sensor.flur_luft_humidity")
        temp_state = self.hass.get_state(entity_id="sensor.flur_luft_temperature")
        return f"{temp_state.state}C {rh_state.state}rH {float(co2_state.state):.0f}ppm {pm25_state.state}ug/m3 {voc_state.state}VOC"

    def update_display(self):
        now = time.time()
        now_str = time.strftime("%d.%m.%Y %H:%M")
        if not self.display_on:
            self.display.send_static_text("")
            return

        texts = [
            {
                'text': now_str,
                'x': 0,
                'y': 7,
                'font': 67
            },
            {
                'text': self.get_default_screen_text(),
                'x': 0,
                'y': 15,
                'font': 65,
                'duration': CYCLE_TIME_SECONDS
            }
        ]
        for notification in self.notifications:
            timestamp, text = notification
            seconds = round(now - timestamp)
            if seconds >= 3600:
                hours = seconds // 3600
                if hours == 1:
                    relative_str = f"{hours} hour ago"
                else:
                    relative_str = f"{hours} hours ago"
            elif seconds >= 60:
                minutes = seconds // 60
                if minutes == 1:
                    relative_str = f"{minutes} minute ago"
                else:
                    relative_str = f"{minutes} minutes ago"
            else:
                # For fresh notifications, show them as a scrolling text for the first minute
                # self.notifications is sorted by newest first, so returning after this is fine
                texts = [
                    {
                        'text': text,
                        'x': 0,
                        'y': 0,
                        'font': 97,
                        'area': (0, 0, 144, 16),
                        'effect': self.display.EFFECT_SCROLL_RTL,
                        'effect_cycles': 0,
                        'effect_time': 0,
                        'effect_speed': 60
                    }
                ]
                self.display.send_texts(texts, use_effects=True)
                return

            texts += [
                {
                    'text': relative_str,
                    'x': 0,
                    'y': 7,
                    'font': 67
                },
                {
                    'text': text,
                    'x': 0,
                    'y': 15,
                    'font': 65,
                    'duration': CYCLE_TIME_SECONDS
                }
            ]
        del texts[-1]['duration'] # To avoid weird black screen inbetween cycles
        self.display.send_texts(texts, use_effects=False)

    def stop(self):
        self.running = False

    def loop(self):
        last_minute = ""
        while self.running:
            now = time.time()
            minute = time.strftime("%M")

            # Remove old notifications
            for notification in list(self.notifications): # iterate over copy
                timestamp, text = notification
                if now - timestamp >= NOTIFICATION_DURATION_SECONDS:
                    self.notifications.remove(notification)

            # Update display on minute change
            if minute != last_minute:
                self.update_display()
                last_minute = minute

            time.sleep(1)


@app.route("/notify.json", methods=["GET", 'POST'])
def rest_notify():
    if 'message' in request.args:
        display.notify(request.args.get('message'))
    return Response(json.dumps({"test": True}), mimetype='application/json')

@app.route("/switch.json", methods=["GET", 'POST'])
def rest_switch():
    if request.method == "POST":
        if request.data == b"ON":
            display.set_state(True)
        elif request.data == b"OFF":
            display.set_state(False)
    return Response("ON" if display.get_state() else "OFF", mimetype='application/json')


hass = Client(HASS_API_URL, HASS_TOKEN, cache_session=False)
display = NotificationDisplay(port="/dev/serial/by-path/pci-0000:00:14.0-usb-0:4:1.0-port0", address=6, home_assistant=hass)

if __name__ == "__main__":
    display_thread = threading.Thread(target=display.loop)
    print("Starting display thread")
    display_thread.start()
    print("Starting server")
    app.run(host="0.0.0.0", port=2343)
    print("Server stopped")
    print("Stopping display thread")
    display.stop()
