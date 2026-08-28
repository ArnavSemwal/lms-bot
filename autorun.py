import time
import subprocess
import datetime
import sys

CHECK_INTERVAL = 3600 

print("🟢 LMS Bot Background Runner Started!")
print("Is window ko minimize karke chhod de. Bot apna kaam karta rahega.\n")

while True:
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] Running LMS check...")
    
    subprocess.run([sys.executable, "main.py"])
    
    print(f"[{current_time}] Check complete. Sleeping for 1 hour...\n")
    time.sleep(CHECK_INTERVAL)
