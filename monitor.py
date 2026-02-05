import requests
import zipfile
import io
import csv
import os
import sys

# --- CONFIGURATION ---
# The FAA stores N-Numbers in the database WITHOUT the 'N'. 
# So N704AX becomes just "704AX"
TARGET_N_NUMBER = "704AX" 
FAA_DB_URL = "https://registry.faa.gov/database/ReleasableAircraft.zip"
NTFY_TOPIC = os.environ.get('NTFY_TOPIC')

def send_push_notification(message, priority='default'):
    """Sends a push notification to your phone via ntfy.sh"""
    if not NTFY_TOPIC:
        print("Warning: NTFY_TOPIC secret is missing. Cannot send notification.")
        return

    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode(encoding='utf-8'),
            headers={
                "Title": f"Archer N{TARGET_N_NUMBER} Update",
                "Priority": priority,
                "Tags": "airplane,warning"
            }
        )
        print("Notification sent!")
    except Exception as e:
        print(f"Failed to send notification: {e}")

def check_database():
    print(f"Downloading FAA Database from {FAA_DB_URL}...")
    
    # Use a browser-like header to be polite
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # Download the ZIP file (stream=True for better memory usage)
        response = requests.get(FAA_DB_URL, headers=headers, stream=True)
        response.raise_for_status()
    except Exception as e:
        print(f"Critical Error downloading database: {e}")
        sys.exit(1)

    print("Download complete. Processing MASTER.txt...")

    # Open the ZIP file in memory
    found_aircraft = False
    
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # The 'MASTER.txt' file contains the main registration info
        with z.open('MASTER.txt') as f:
            # Decode the bytes to text
            text_file = io.TextIOWrapper(f, encoding='utf-8-sig', errors='replace')
            # Read as a dictionary (auto-detects headers like 'N-NUMBER', 'AIR WORTH DATE')
            reader = csv.DictReader(text_file)
            
            # Print headers for debugging if needed
            # print(f"Headers found: {reader.fieldnames}")

            for row in reader:
                # CORRECTED LINE: Access the specific 'N-NUMBER' column
                current_n_number = row.get('N-NUMBER', '').strip()
                
                if current_n_number == TARGET_N_NUMBER:
                    found_aircraft = True
                    
                    # EXTRACT DATA using correct column headers
                    aw_date = row.get('AIR WORTH DATE', '').strip()
                    status = row.get('STATUS CODE', '').strip()
                    
                    print(f"--- DATA FOUND FOR N{TARGET_N_NUMBER} ---")
                    print(f"Status Code: {status} (V=Valid)")
                    print(f"Airworthiness Date: '{aw_date}'")
                    
                    # LOGIC: 
                    # If 'AIR WORTH DATE' is NOT empty, it means the certificate exists.
                    if aw_date:
                        msg = f"URGENT: Airworthiness Certificate ISSUED for N{TARGET_N_NUMBER}! Date: {aw_date}. Check FAA Registry now."
                        print("TRIGGER: Certificate Detected!")
                        send_push_notification(msg, priority='high')
                    else:
                        print("Result: No Airworthiness Date listed yet.")
                    
                    break # Stop searching once found

    if not found_aircraft:
        print(f"Error: Could not find record for {TARGET_N_NUMBER} in the database.")
        sys.exit(1)

if __name__ == "__main__":
    check_database()
