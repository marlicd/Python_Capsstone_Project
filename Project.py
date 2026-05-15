import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import sqlite3
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


# PAGE CONFIG


st.set_page_config(
    page_title="F1 Weather Forecast",
    page_icon="🏎",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# DATABASE SETUP


DB_PATH = "races.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS races (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_name TEXT,
            city TEXT,
            date TEXT,
            ticket_url TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_races_to_db(races):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM races")
    for race in races:
        cursor.execute(
            "INSERT INTO races (race_name, city, date, ticket_url) VALUES (?, ?, ?, ?)",
            (race["race"], race["city"], race["date"], race["ticket_url"])
        )
    conn.commit()
    conn.close()

def get_races_from_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT race_name, city, date, ticket_url FROM races")
    rows = cursor.fetchall()
    conn.close()
    return [{"race": r[0], "city": r[1], "date": r[2], "ticket_url": r[3]} for r in rows]


# SCRAPE THE F1 CALENDAR FROM WIKIPEDIA


def scrape_races():
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
        return []

    rows = race_table.find_all("tr")

    races = []

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

            country_slugs = {
                "Australian Grand Prix": "australia",
                "Chinese Grand Prix": "china",
                "Japanese Grand Prix": "japan",
                "Bahrain Grand Prix": "bahrain",
                "Saudi Arabian Grand Prix": "saudi-arabia",
                "Miami Grand Prix": "miami",
                "Emilia Romagna Grand Prix": "emilia-romagna",
                "Monaco Grand Prix": "monaco",
                "Canadian Grand Prix": "canada",
                "Spanish Grand Prix": "spain",
                "Austrian Grand Prix": "austria",
                "British Grand Prix": "great-britain",
                "Belgian Grand Prix": "belgium",
                "Hungarian Grand Prix": "hungary",
                "Dutch Grand Prix": "netherlands",
                "Italian Grand Prix": "italy",
                "Azerbaijan Grand Prix": "azerbaijan",
                "Singapore Grand Prix": "singapore",
                "United States Grand Prix": "united-states",
                "Mexico City Grand Prix": "mexico",
                "São Paulo Grand Prix": "brazil",
                "Las Vegas Grand Prix": "las-vegas",
                "Qatar Grand Prix": "qatar",
                "Abu Dhabi Grand Prix": "abu-dhabi",
            }

            slug = country_slugs.get(race_name, race_name.lower().replace(" ", "-"))
            ticket_url = f"https://www.formula1.com/en/racing/2026/{slug}"

            races.append({
                "race": race_name,
                "city": city,
                "date": date,
                "ticket_url": ticket_url
            })

    return races

def parse_race_date(date_str):
    return datetime.strptime(date_str + " 2026", "%d %B %Y")


# GET WEATHER FOR A CITY


def get_weather(city):
    API_KEY = os.getenv("OPENWEATHER_API_KEY")
    if not API_KEY:
        return {"error": "API key not found. Check your .env file."}

    base_url = "https://api.openweathermap.org/data/2.5/forecast?"
    weather_url = f"{base_url}appid={API_KEY}&q={city}&units=metric"

    weather_response = requests.get(weather_url)
    weather_data = weather_response.json()

    if "list" not in weather_data:
        return {"error": weather_data.get("message", "Unknown error")}

    FORECAST_LIMIT = 5

    forecast = []
    temps = []

    for item in weather_data["list"]:
        time = item["dt_txt"]
        if "12:00:00" in time:
            temp = item["main"]["temp"]
            condition = item["weather"][0]["description"]
            forecast.append({
                "Date / Time": time,
                "Temp (°C)": round(temp, 1),
                "Conditions": condition.capitalize()
            })
            temps.append(temp)

    avg_temp = round(sum(temps) / len(temps), 1) if temps else None

    if avg_temp is not None:
        if avg_temp > 30:
            advice = "Very hot. Wear light clothes, sunglasses, and stay hydrated."
        elif avg_temp > 20:
            advice = "Warm weather. T-shirts and light clothing are fine."
        elif avg_temp > 10:
            advice = "Cool weather. Wear a jacket or hoodie."
        else:
            advice = "Cold weather. Wear heavy jackets and warm clothing."
    else:
        advice = "No temperature data available."

    return {
        "forecast": forecast,
        "avg_temp": avg_temp,
        "advice": advice
    }


# INITIALISE DB AND LOAD RACES


init_db()

if "races" not in st.session_state:
    scraped = scrape_races()
    if scraped:
        save_races_to_db(scraped)
    st.session_state.races = get_races_from_db()

today = datetime.now()

upcoming = [
    r for r in st.session_state.races
    if parse_race_date(r["date"]) > today
]
upcoming.sort(key=lambda x: parse_race_date(x["date"]))


# PAGE HEADER


st.title("🏎 F1 Race Day Weather")
st.caption("2026 Season")

st.divider()


# ABOUT THIS PROJECT


st.subheader("What is this?")

st.write(
    "A lot of F1 fans who go to watch the races in person end up getting caught off guard by the weather. "
    "You show up on race day and it is either blazing hot or suddenly raining, and the next thing you know "
    "you are buying an overpriced poncho or squeezing into a shade that is already full. "
    "This happens because the weather at race circuits around the world changes constantly and is hard to predict "
    "without actually checking the forecast for that specific city."
)

st.write(
    "This tool solves that. It pulls the full 2026 F1 race calendar straight from Wikipedia, stores it, "
    "and then checks the live weather forecast for the city where each race is taking place. "
    "That way you can plan ahead — know what to wear, what to pack, and what to expect before you even book your travel."
)

col1, col2, col3 = st.columns(3)

with col1:
    st.info("**The Problem**\n\nFans attending races in person often have no idea what the weather will be like on race day. Wind, rain, and heat vary a lot depending on the country and time of year.")

with col2:
    st.info("**The Solution**\n\nThis tool fetches a live weather forecast for each race city. If the race is too far away for an exact forecast, it shows the nearest available data as a guide.")

with col3:
    st.info("**Who It Helps**\n\nAnyone planning to attend a race in person. It gives you enough information to pack the right clothes and not get caught out on the day.")

st.divider()


# NEXT RACE BANNER


if upcoming:
    next_race = upcoming[0]
    days_until_next = (parse_race_date(next_race["date"]) - today).days

    st.subheader("Next Race")
    st.success(f"**{next_race['race']}** — {next_race['city']} — {next_race['date']} ({days_until_next} days away)")

st.divider()


# RACE CALENDAR


st.subheader("2026 Race Calendar")
st.write("Click on a race below to see the weather forecast for that city and what you should wear.")

st.write("")

if not upcoming:
    st.warning("No upcoming races found.")
else:
    for i, race in enumerate(upcoming):
        days_until = (parse_race_date(race["date"]) - today).days

        is_next = i == 0
        label = f"{'[ NEXT ]  ' if is_next else ''}{str(i + 1).zfill(2)}  —  {race['race']}  |  {race['city']}  |  {race['date']}"

        with st.expander(label):

            st.write("**Race:**", race["race"])
            st.write("**City:**", race["city"])
            st.write("**Date:**", race["date"])
            st.write("**Days away:**", days_until)

            st.write("")

            weather = get_weather(race["city"])

            if "error" in weather:
                st.error("Could not load weather data: " + weather["error"])

            else:
                FORECAST_LIMIT = 5

                if days_until > FORECAST_LIMIT:
                    st.warning(
                        "The exact forecast for race day is not available yet. "
                        "The " + race["race"] + " is " + str(days_until) + " days away, which is further than the 5-day forecast window. "
                        "The forecast below is for " + race["city"] + " right now and gives you a good idea of the kind of conditions to expect."
                    )

                if weather["forecast"]:
                    df = pd.DataFrame(weather["forecast"])
                    st.dataframe(df, width="stretch", hide_index=True)
                else:
                    st.write("No forecast data available for this city.")

                st.write("")
                st.write("**What to wear:**", weather["advice"])

                if days_until > FORECAST_LIMIT:
                    st.caption("Average temp over the available forecast: " + str(weather["avg_temp"]) + " °C. Keep in mind conditions may be different on race day itself.")

                st.write("")
                st.link_button("Buy Tickets on F1.com", race["ticket_url"])


# FOOTER


st.divider()
st.caption("Race data scraped from Wikipedia. Weather data from OpenWeatherMap. | formula1.com")