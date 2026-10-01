import time
import subprocess
import datetime
import sys
import os
from dotenv import load_dotenv

load_dotenv()

try:
    hours = float(os.getenv("CHECK_INTERVAL_HOURS", 4))
except ValueError:
    hours = 4.0

CHECK_INTERVAL = int(hours * 3600)

print("🟢 LMS Bot Background Runner Started!")
print(f"Interval set to {hours} hours. (You can change this in your .env file)")
print("Is window ko minimize karke chhod de. Bot apna kaam karta rahega.\n")

while True:
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] Running LMS check...")
    
    subprocess.run([sys.executable, "main.py"])
    
    print(f"[{current_time}] Check complete. Sleeping for {hours} hours...\n")
    time.sleep(CHECK_INTERVAL)
