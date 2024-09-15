import datetime
import pytz

def get_date_time():
    """
    Returns the current date and time in Tennessee, USA.
    """
    tz = pytz.timezone('America/Chicago')  # Tennessee is in the Central Time Zone
    current_time = datetime.datetime.now(tz)
    return current_time.strftime("%Y-%m-%d %H:%M:%S %Z")

# You can add more functions here in the future