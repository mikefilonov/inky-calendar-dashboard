# How to Run and Develop Inky Calendar

This document guides you on how to set up your local development environment, run offline preview renders, and deploy the project to your Raspberry Pi.

---

## 💻 Local Development Setup (Offline Rendering)

For fast development cycles, you can run the calendar engine offline on your computer. It reads calendar event data from the anonymized test calendar file (`tests/data/test_calendar.ics`) and generates layout previews.

1. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

2. **Install local development dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the offline test suite and generate previews**:
   ```bash
   python3 run_tests.py all
   ```
   This will parse the test data and output layout previews:
   - Grid layout: `tests/outputs/test_calendar_render_grid.png`
   - List layout: `tests/outputs/test_calendar_render_list.png`
   - Default preview (Grid): `calendar.png` (in root directory)

---

## 🚀 Easy Deployment (Automated Script)

The easiest way to deploy updates from your local computer to the Raspberry Pi is using the bundled **`deploy.sh`** script. 

Run this command from your computer terminal:
```bash
./deploy.sh <user>@<pi-ip-or-host>
# Example:
./deploy.sh mikefilonov@192.168.69.73
```

This automated deployment script will:
1. Copy the source files to the Pi (excluding local `venv/`, `calendar.png`, and `config.json`).
2. Verify and install system dependencies (like `python3-dev`) on the Pi.
3. Configure the Python virtual environment and install pip dependencies on the Pi.
4. Set up/update the cron job and reboot tasks automatically on the Pi.
5. Perform an initial forced render on the Pi display.
6. Pull the generated `calendar.png` back to your local computer for instant layout validation.

---

## 🛠️ Manual Raspberry Pi Setup

If you prefer to configure the Pi manually, follow the steps below.

### Step 1: Ensure Hardware Interfaces are Enabled
The Inky Impression display requires SPI and I2C hardware protocols to communicate:
1. Open the Raspberry Pi configuration tool:
   ```bash
   sudo raspi-config
   ```
2. Navigate to **Interface Options**.
3. Enable both **SPI** and **I2C**.
4. Save and reboot your Pi.

### Step 2: Configure `config.json`
1. Copy the example configuration:
   ```bash
   cp config.json.example config.json
   ```
2. Retrieve your Google Calendar Secret iCal Address:
   * Go to **Google Calendar** on a web browser.
   * Under "My calendars", hover over your calendar, click the options icon (three vertical dots), and select **Settings and sharing**.
   * Scroll down to the **Integrate calendar** section.
   * Copy the **Secret address in iCal format** URL.
3. Populate `config.json` (on the Pi or locally before deploying):
   ```json
   {
     "calendar_url": "YOUR_SECRET_ICAL_URL_HERE",
     "timezone": "America/Los_Angeles",
     "dry_run": false,
     "resolution": [800, 480],
     "renderer": "grid"
   }
   ```
   * `"dry_run": false`: Set to `true` to skip hardware refresh and save previews to `calendar.png` locally on the Pi.
   * `"renderer": "grid"`: Selects the 2-Column layout. Use `"list"` for the legacy chronological list layout.

### Step 3: Run Manually
To test execution on the Pi manually:
```bash
~/inky-calendar/venv/bin/python ~/inky-calendar/main.py --force
```

### Step 4: Automate Updates (Cron Job)
1. Open the cron scheduler for your user:
   ```bash
   crontab -e
   ```
2. Add a line to run the calendar script every 5 minutes and on system startup:
   ```cron
   */5 * * * * /home/<user>/inky-calendar/venv/bin/python /home/<user>/inky-calendar/main.py >> /home/<user>/inky-calendar/cron.log 2>&1
   @reboot sleep 30 && /home/<user>/inky-calendar/venv/bin/python /home/<user>/inky-calendar/main.py --force >> /home/<user>/inky-calendar/cron.log 2>&1
   ```
