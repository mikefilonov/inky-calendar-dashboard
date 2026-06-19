# Inky Calendar

A Python-based e-ink calendar dashboard designed for Raspberry Pi. It fetches events from Google Calendar (via private iCal feeds), parses recurrence rules, and renders a highly legible layout optimized for 7-color e-paper displays.

---

<img width="800" height="480" alt="calendar" src="https://github.com/user-attachments/assets/6a63053d-7791-42aa-921d-74ea4dd03dee" />


## 🛠️ Hardware Requirements

* **Raspberry Pi**: Any Raspberry Pi model with GPIO headers (e.g. Raspberry Pi 3, 4, 5, or Zero 2 W) running Raspberry Pi OS.
* **E-paper Display**: **Pimoroni Inky Impression 7.3"** 7-color e-ink display (specifically detected as the **Spectra 6 800x480 (E673)** panel).
* **Communication Protocols**: Requires SPI and I2C interfaces enabled on the Raspberry Pi.

---

## 💻 Software Stack & Dependencies

The project is built on **Python 3** and utilizes the following key libraries:

* **Pimoroni `inky`**: Library to communicate with the Inky Impression hardware and manage its 7-color palette (Spectra 6).
* **Pillow (`PIL`)**: Used for drawing shapes, rendering layouts, wrapping text, and outputting crisp images.
* **`icalendar` & `python-dateutil`**: Core parser engines that load `.ics` calendar files and compute complex recurrence rules (`RRULE`).
* **`pytz`**: Handles accurate local timezone calculations.
* **`requests`**: Handles downloading Google Calendar iCal feeds.
* **`spidev` & `smbus2`**: Low-level SPI and I2C hardware interface bindings for Linux/Raspberry Pi.

---

## 🎨 Rendering Layouts

The project features a configuration-driven switchable rendering engine:

1. **List Layout (`list`)**:
   - A list of schedule rows. Shows today with a thick highlighted outline and stacks upcoming days below it. Perfect for simple chronological schedules.
2. **Dynamic 2-Column Layout (`grid`)** *[Active]*:
   - Optimized for maximum readability.
   - **Today (Left Column)**: Occupies 60% of the screen. Shows massive colored event cards (`size 26` bold title text) for high visibility.
   - **Upcoming Days (Right Column)**: Collapses tomorrow and the day after tomorrow vertically into lists. Uses a size-highlighted text format with a vertical left accent bar corresponding to the event owner's color coding.

---

## ⚙️ Configuration

Create a `config.json` in the root folder (see `config.json.example`):

```json
{
  "calendar_url": "YOUR_GOOGLE_CALENDAR_SECRET_ICAL_URL",
  "timezone": "America/Los_Angeles",
  "dry_run": false,
  "resolution": [800, 480],
  "renderer": "grid"
}
```

* Set `"dry_run": true` for local development. It will bypass the hardware check and save the preview directly as `calendar.png`.
* Set `"renderer": "grid"` to select the 2-Column layout, or `"list"` for the list layout.

---

## 🚀 How to Run & Deploy

For step-by-step instructions on setting up SPI/I2C interfaces, configuring virtual environments, installing remote services, and automating execution with a Cron job on the Pi, please refer to the detailed deployment documentation in [RUN.md](file:///Users/mikefilonov/Documents/diy-project/inky-calendar/RUN.md).

To run locally and inspect the test render:
```bash
python3 test_render.py grid
```
This saves a simulated render to [calendar.png](file:///Users/mikefilonov/Documents/diy-project/inky-calendar/calendar.png).
