from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import pandas as pd
import time
import os
import subprocess
import glob

# Configure WebDriver
options = webdriver.ChromeOptions()
download_path = "your/download/path"
prefs = {
    "download.default_directory": download_path,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)
driver = webdriver.Chrome(options=options)

# Open Kahoot Login Page
driver.get("https://create.kahoot.it/auth/login")

# Reject Cookies
try:
    reject_cookies_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reject all cookies')]")
        )
    )
    reject_cookies_button.click()
    print("Cookies rejected.")
except Exception as e:
    print("No cookie banner found:", e)

# Log In
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))
username = driver.find_element(By.NAME, "username")
password = driver.find_element(By.NAME, "password")
username.send_keys("yourname@gmail.com")  # Replace securely
password.send_keys("yourpassword")  # Replace securely
password.send_keys(Keys.RETURN)

WebDriverWait(driver, 10).until(EC.url_changes("https://create.kahoot.it/auth/login"))

# Navigate to Reports Page
driver.get("https://create.kahoot.it/user-reports/hosted-by-me/list/?searchMode=host&globalFilter=liveGame&orderBy=time&reverse=true")

# Click Action Menu
try:
    action_menu_button = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.XPATH, "//button[@data-functional-selector='report-action-menu__toggle']"))
    )
    action_menu_button.click()
    print("Action menu clicked.")
    time.sleep(2)
except Exception as e:
    print("Error clicking the action menu:", e)

# Click "Download report"
try:
    download_report_item = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.XPATH, "//div[@role='menuitem' and @data-functional-selector='report-action-menu__download']"))
    )
    download_report_item.click()
    print("Download report clicked.")
    time.sleep(2)
except Exception as e:
    print("Error clicking download report:", e)

# Click Final Download Button
try:
    final_download_button = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.XPATH, "//button[normalize-space()='Download']"))
    )
    final_download_button.click()
    print("Final Download button clicked.")
    time.sleep(5)
except Exception as e:
    print("Error clicking the final Download button:", e)

driver.quit()

# Process Excel File
def get_latest_file(path):
    files = glob.glob(os.path.join(path, "*"))
    if not files:
        return None
    return max(files, key=os.path.getctime)

print("Waiting for file to finish downloading...")
time.sleep(5)
latest_file = get_latest_file(download_path)

if latest_file:
    print(f"Latest file detected: {latest_file}")
else:
    print("No file found.")
    exit()

try:
    df = pd.read_excel(latest_file, sheet_name=1, header=2)
    print("Data loaded successfully.")
except Exception as e:
    print("Error reading Excel file:", e)
    exit()

required_cols = ["Rank", "Player", "Total Score (points)", "Correct Answers"]
missing = [col for col in required_cols if col not in df.columns]
if missing:
    print(f"Missing columns in the Excel file: {missing}")
    exit()

# Compute Grades
def compute_letter_grade(score):
    if score >= 92:
        return "10"
    elif score >= 82:
        return "9"
    elif score >= 72:
        return "8"
    elif score >= 63:
        return "7"
    elif score >= 57:
        return "6"
    elif score >= 50:
        return "5"
    else:
        return "4"

def calculate_numeric_grade(row):
    correct_answers = row["Correct Answers"] if row["Correct Answers"] else 0
    if correct_answers == 0:
        return 0
    return row["Total Score (points)"] / (correct_answers * 10)

df["NumericGrade"] = df.apply(calculate_numeric_grade, axis=1)
df["LetterGrade"] = df["NumericGrade"].apply(compute_letter_grade)

# Save Results to Text File
text_file_path = os.path.join(download_path, "grades.txt")
with open(text_file_path, "w", encoding="utf-8") as text_file:
    # Get first 5 results using head(5)
    for idx, row in df.head(5).iterrows():  # Modified line
        player = row.get("Player", "Unknown")
        rank = row.get("Rank", "N/A")
        numeric_grade = row.get("NumericGrade", 0)
        letter_grade = row.get("LetterGrade", "N/A")
        text = f"Nxënësi {player} ka zënë vendin numër {rank}, me  {numeric_grade:.1f} pikë, me notën {letter_grade}.\n"
        text_file.write(text)
    print("Top 5 results saved to text file.")

# STEP 1: Generate TTS with Neura.al (Your Working Version)
with open(text_file_path, "r", encoding="utf-8") as file:
    text = file.read()

NEURA_API_KEY = "your-api-key"  # Replace if needed
tts_url = "https://neura.al/api/v1.5/tts"
tts_data = {
    "keyId": NEURA_API_KEY,
    "text": text,
    "speaker": "f1"  # Change voice if needed (e.g., "m1" for male)
}
headers = {"Authorization": f"Bearer {NEURA_API_KEY}"}
response = requests.post(tts_url, json=tts_data, headers=headers)

if response.status_code != 200:
    print("Neura TTS Error:", response.json())
    exit()

callback_id = response.json().get("callbackID")
print(f"Neura TTS Request Sent! Callback ID: {callback_id}")

# Poll Neura TTS Status
status_url = f"https://neura.al/api/v1.5/callback/status?callbackId={callback_id}"
while True:
    status_response = requests.get(status_url, headers=headers)
    status_data = status_response.json()

    if status_data.get("status") == "done":
        print("Neura TTS Audio Ready!")
        audio_url = status_data.get("data")[0].get("result")  # Extract URL
        break
    elif status_data.get("status") == "failed":
        print("Neura TTS Failed:", status_data)
        exit()
    time.sleep(3)

# Download Neura TTS Audio
audio_response = requests.get(audio_url)
if audio_response.status_code == 200:
    audio_path = os.path.join(download_path, "grades_speech.mp3")
    with open(audio_path, "wb") as f:
        f.write(audio_response.content)
    print(f"Saved Neura TTS Audio: {audio_path}")
else:
    print("Failed to download Neura audio.")
    exit()

# STEP 2: Lip-Sync with Everypixel
EVERYPIXEL_CLIENT_ID = "your-client-id"  # Replace with your credentials
EVERYPIXEL_CLIENT_SECRET = "your-everypixel-client-secret"
input_video_path = "input_video.mp4"  # Ensure this file exists

# Convert MP3 to WAV (required for Everypixel)
wav_path = os.path.join(download_path, "grades_speech.wav")
subprocess.run(["ffmpeg", "-i", audio_path, wav_path])

# Upload to Everypixel Lipsync
with open(wav_path, "rb") as audio_file, open(input_video_path, "rb") as video_file:
    lipsync_response = requests.post(
        "https://api.everypixel.com/v1/lipsync/create",
        files={
            "audio": ("grades_speech.wav", audio_file),
            "video": ("input_video.mp4", video_file)
        },
        auth=(EVERYPIXEL_CLIENT_ID, EVERYPIXEL_CLIENT_SECRET)
    )

if lipsync_response.status_code != 201:
    print("Everypixel Lipsync Error:", lipsync_response.json())
    exit()

lipsync_task_id = lipsync_response.json().get("task_id")
print(f"Everypixel Lipsync Task Created! ID: {lipsync_task_id}")

# Poll Lipsync Status
lipsync_status_url = f"https://api.everypixel.com/v1/lipsync/status?task_id={lipsync_task_id}"
while True:
    status_response = requests.get(lipsync_status_url, auth=(EVERYPIXEL_CLIENT_ID, EVERYPIXEL_CLIENT_SECRET))
    status_data = status_response.json()

    if status_data.get("status") == "SUCCESS":
        output_video_url = status_data.get("result")
        print("Lipsync Complete! Downloading video...")
        break
    elif status_data.get("status") in ["FAILURE", "REVOKED"]:
        print("Lipsync Failed:", status_data)
        exit()
    time.sleep(10)

# Download Final Lip-Synced Video
output_video_path = os.path.join(download_path, "lip_synced_video.mp4")
video_response = requests.get(output_video_url)
if video_response.status_code == 200:
    with open(output_video_path, "wb") as f:
        f.write(video_response.content)
    print(f"Final Video Saved: {output_video_path}")
else:
    print("Failed to download lipsynced video.")

print("Process Complete! Check the output video.")
