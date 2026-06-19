# How to Run the Inky Calendar on your Raspberry Pi

Follow these steps to deploy, configure, and automate the new calendar project on your Raspberry Pi.

---

## Step 1: Transfer the Project to your Pi
Copy the `inky-calendar` directory from your Mac to your Raspberry Pi, or clone it if you pushed it to a Git remote:
```bash
# Example command using rsync from your Mac terminal:
rsync -avz --exclude 'venv' --exclude 'calendar.png' --exclude 'config.json' /Users/mikefilonov/Documents/diy-project/inky-calendar/ pi@<your-pi-ip>:~/inky-calendar/
```

---

## Step 2: Ensure Hardware Interfaces are Enabled
The Inky Impression display communicating with python requires the SPI and I2C interfaces.
1. Open the configuration tool on your Pi:
   ```bash
   sudo raspi-config
   ```
2. Navigate to **Interface Options**.
3. Enable both **SPI** and **I2C**.
4. Finish and reboot.

---

## Step 3: Setup Virtual Environment & Install Libraries
On your Pi, set up a Python virtual environment and install the dependencies (including `inky` and `smbus2` which are required to control the hardware):

```bash
cd ~/inky-calendar

# Create python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (on Pi, this includes the hardware libraries automatically)
pip install --upgrade pip
pip install -r requirements.txt
pip install inky smbus2
```

---

## Step 4: Configure your Google Calendar URL
1. Copy the example configuration to `config.json` if you haven't already:
   ```bash
   cp config.json.example config.json
   ```
2. Get your Google Calendar Secret iCal Address:
   * Go to **Google Calendar** on a browser.
   * Under "My calendars", hover over your calendar, click the three dots, and select **Settings and sharing**.
   * Scroll down to the **Integrate calendar** section.
   * Copy the **Secret address in iCal format** URL.
3. Edit `config.json` on the Pi (using `nano config.json`):
   ```json
   {
     "calendar_url": "YOUR_SECRET_ICAL_URL_HERE",
     "timezone": "America/Los_Angeles",
     "dry_run": false,
     "resolution": [800, 480]
   }
   ```
   * *Note: Ensure `"dry_run"` is set to `false` so it pushes the layout to the screen instead of saving a file.*

---

## Step 5: Test Execution
Run the script manually to ensure it correctly downloads your calendar and draws it on the screen:
```bash
~/inky-calendar/venv/bin/python ~/inky-calendar/main.py
```

---

## Step 6: Automate Updates (Cron Job)
E-ink displays only need to be updated when things change. Updating every 15 to 30 minutes is ideal.
1. Open the cron scheduler for your user:
   ```bash
   crontab -e
   ```
2. Add a line to run the script every 30 minutes (direct stdout/stderr to a log file for debugging):
   ```cron
   */30 * * * * /home/pi/inky-calendar/venv/bin/python /home/pi/inky-calendar/main.py >> /home/pi/inky-calendar/cron.log 2>&1
   ```
