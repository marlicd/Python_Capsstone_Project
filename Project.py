import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()


# SCRAPE THE F1 CALENDAR FROM WIKIPEDIA

url = "https://en.wikipedia.org/wiki/2026_Formula_One_World_Championship"

headers = {"User-Agent": "Mozilla/5.0"}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

tables = soup.find_all("table", class_="wikitable")

race_table = None

for table in tables:
    if "Grand Prix" in table.get_text():
        race_table = table
        break

if race_table is None:
    print(" Could not find race calendar table")
    exit()

rows = race_table.find_all("tr")

races = []

print("=== 2026 F1 RACE CALENDAR ===\n")

for row in rows:
    cols = row.find_all("td")

    if len(cols) >= 3:
        race_name = cols[0].get_text(strip=True)

        circuit_info = cols[1].get_text(" ", strip=True)
        circuit_info = circuit_info.replace("|", ",")

        parts = [p.strip() for p in circuit_info.split(",") if p.strip()]
        city = parts[-1] if parts else "Unknown"

        raw_date = cols[2].get_text(" ", strip=True)
        date = re.sub(r"\[.*?\]", "", raw_date).strip()

        races.append({
            "race": race_name,
            "city": city,
            "date": date
        })

# FIND NEXT RACE FROM THE SCRAPED DATA

today = datetime.now()

def parse_race_date(date_str):
    return datetime.strptime(date_str + " 2026", "%d %B %Y")

races.sort(key=lambda x: parse_race_date(x["date"]))

next_race = None

for race in races:
    if parse_race_date(race["date"]) > today:
        next_race = race
        break

if not next_race:
    print(" No upcoming race found")
    exit()

print("\n NEXT RACE:")
print("Race:", next_race["race"])
print("City:", next_race["city"])
print("Date:", next_race["date"])


# GET THE WEATHER  OF THE CITY WHERE THE RACE IS SET TO TAKE PLACE


API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not API_KEY:
    print("API key not found. Check your .env file.")
    

city = next_race["city"]

print("\n Weather City:", city)

base_url = "https://api.openweathermap.org/data/2.5/forecast?"

weather_url = f"{base_url}appid={API_KEY}&q={city}&units=metric"

weather_response = requests.get(weather_url)
weather_data = weather_response.json()

if "list" not in weather_data:
    print(" Weather API Error:", weather_data.get("message", "Unknown error"))
    exit()

print("\n Weather Forecast:\n")

temps = []

for item in weather_data["list"]:
    time = item["dt_txt"]

    if "12:00:00" in time:
        temp = item["main"]["temp"]
        condition = item["weather"][0]["description"]

        print(time, "-", temp, "°C -", condition)
        temps.append(temp)


# GIVE CLOTHING ADVICE TP THE USERS


if temps:
    avg_temp = sum(temps) / len(temps)

    print("\n Clothing Advice:")

    if avg_temp > 30:
        print("Very hot. Wear light clothes, sunglasses, and stay hydrated.")
    elif avg_temp > 20:
        print("Warm weather. T-shirts and light clothing are fine.")
    elif avg_temp > 10:
        print("Cool weather. Wear a jacket or hoodie.")
    else:
        print("Cold weather. Wear heavy jackets and warm clothing.")
else:
    print("\n No temperature data found.")