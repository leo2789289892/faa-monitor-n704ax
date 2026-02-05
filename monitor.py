import requests
from bs4 import BeautifulSoup
import os
import sys

# --- CONFIGURATION ---
N_NUMBER = "704AX"
TARGET_URL = f"https://registry.faa.gov/AircraftInquiry/Search/NNumberResult?nNumberTxt={N_NUMBER}"
NTFY_TOPIC = os.environ.get('NTFY_TOPIC')

def send_push_notification(message, priority='default'):
    """
    Sends a push notification to the mobile device via ntfy.sh.
    """
    if not NTFY_TOPIC:
        print("Error: NTFY_TOPIC environment variable not set.")
        return

    try:
        resp = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode(encoding='utf-8'),
            headers={
                "Title": f"FAA Registry Alert: {N_NUMBER}",
                "Priority": priority,
                "Tags": "airplane,warning"
            }
        )
        resp.raise_for_status()
        print("Notification sent successfully.")
    except Exception as e:
        print(f"Failed to send notification: {e}")

def check_registry():
    print(f"Checking FAA Registry for {N_NUMBER}...")
    
    # 1. Masquerade as a browser to avoid bot detection
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching FAA data: {e}")
        # Optional: Notify on failure so you know the monitor is broken
        # send_push_notification(f"Monitor Failed: Could not connect to FAA site.", priority='low')
        sys.exit(1)

    # 2. Parse the HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # 3. Extract Temporary Certificate Status
    # We look for the 'Temporary Certificates' label and then find its value.
    # The FAA site structure uses semantic tables.
    
    temp_cert_value = None
    
    # Strategy: Find the cell containing the label, then find the next cell.
    # Note: The label text might have whitespace, so we use a loose match.
    label_found = False
    for cell in soup.find_all(['td', 'th']):
        if "Temporary Certificates" in cell.get_text():
            label_found = True
            # The value is typically in the next sibling element or the next td
            next_cell = cell.find_next_sibling('td')
            if next_cell:
                temp_cert_value = next_cell.get_text(strip=True)
                break
    
    if not label_found:
        print("Critical Error: Could not find 'Temporary Certificates' label in HTML. FAA may have changed site layout.")
        sys.exit(1)

    print(f"Detected Value: '{temp_cert_value}'")

    # 4. Evaluate and Alert
    if temp_cert_value and "None" not in temp_cert_value:
        # SUCCESS CONDITION: The value is NOT "None". A certificate exists.
        alert_msg = f"URGENT: Temporary Certificate DETECTED for {N_NUMBER}. Value: {temp_cert_value}. Check Registry immediately."
        print("Triggering Alert...")
        send_push_notification(alert_msg, priority='high')
    else:
        print("Status is still 'None'. No alert triggered.")

if __name__ == "__main__":
    check_registry()
