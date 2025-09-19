# Home Assistant notifications on a mobitec next stop display
This is a small REST server that works in conjunction with the RESTful notification integration of Home Assistant.
It displays received notifications on a mobitec next stop display.
It also provides a switch entity that "turns off" the display by sending a blank message if needed.
Furthermore, it shows some sensor states by default that you will most likely need to customize.

# License
GPLv3, see LICENSE file.

# Setup
Just add this to your `configuration.yaml`:

```
notify:
  - platform: rest
    name: Mobitec
    resource: "http://192.168.0.100:2343/notify.json"

switch:
  - platform: rest
    name: Mobitec
    resource: "http://192.168.0.100:2343/switch.json"
```