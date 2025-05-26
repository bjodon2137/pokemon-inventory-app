import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import openai

st.set_page_config(page_title="Pokémon Card Inventory", layout="wide")
st.title("🌟 Pokémon Card Inventory Tracker")

# Password protection
password = st.text_input("Enter password to access:", type="password")
if password != "pikachu123":
    st.stop()

# File uploader
uploaded_file = st.file_uploader("Upload a CSV file with card IDs (one per line):", type=["csv"])

# OpenAI API Key (assumes key is stored as Streamlit secret)
openai.api_key = st.secrets["openai_api_key"]

def get_card_analysis(name, rarity, price):
    prompt = f"""
    Analyze this Pokémon card for a collector: {name}. 
    It has a rarity of '{rarity}' and a current market value of ${price:.2f}.
    Based on general collector advice, would you recommend holding, selling, or keeping as a long-term investment?
    Provide one short sentence of reasoning.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return "AI analysis unavailable."

if uploaded_file is not None:
    # Read card IDs from uploaded file
    card_ids = pd.read_csv(uploaded_file, header=None)[0].tolist()

    api_url = "https://api.pokemontcg.io/v2/cards/"
    headers = {"Accept": "application/json"}
    card_data = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with st.spinner("Fetching card data..."):
        for card_id in card_ids:
            response = requests.get(api_url + card_id, headers=headers)
            if response.status_code == 200:
                card = response.json()['data']
                price = card.get("tcgplayer", {}).get("prices", {}).get("normal", {}).get("market")
                card_info = {
                    "Card ID": card.get("id"),
                    "Name": card.get("name"),
                    "Set": card.get("set", {}).get("name"),
                    "Number": card.get("number"),
                    "Rarity": card.get("rarity"),
                    "Market Price (USD)": price if price is not None else None,
                    "Image URL": card.get("images", {}).get("small"),
                    "Checked On": timestamp
                }
                card_data.append(card_info)

    if card_data:
        df = pd.DataFrame(card_data)
        df["Market Price (USD)"] = pd.to_numeric(df["Market Price (USD)"], errors="coerce")

        # Total value
        total_value = df["Market Price (USD)"].sum()

        # Top 5 cards
        top_cards = df.sort_values(by="Market Price (USD)", ascending=False).head(5)
        top_cards.insert(0, "Top 5", ["#1", "#2", "#3", "#4", "#5"])

        # AI Analysis
        st.subheader("🤖 AI-Powered Card Insights")
        ai_insights = []
        for _, row in df.iterrows():
            if pd.notna(row["Market Price (USD)"]):
                insight = get_card_analysis(row["Name"], row["Rarity"], row["Market Price (USD)"])
            else:
                insight = "No price data available."
            ai_insights.append(insight)
        df["AI Recommendation"] = ai_insights

        st.subheader("📊 Collection Summary")
        st.metric(label="Total Market Value", value=f"${total_value:.2f}")
        st.write(f"Checked on: {timestamp}")

        st.subheader("💼 All Cards")
        st.dataframe(df.drop(columns=["Image URL"]))

        st.subheader("🏆 Top 5 Most Valuable Cards")
        for i, row in top_cards.iterrows():
            col1, col2 = st.columns([1, 6])
            with col1:
                st.image(row["Image URL"], width=80)
            with col2:
                st.markdown(f"**{row['Top 5']} - {row['Name']}**")
                st.markdown(f"Set: {row['Set']} | Price: ${row['Market Price (USD)']:.2f}")

        # Option to download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📁 Download Full Inventory as CSV",
            data=csv,
            file_name='pokemon_card_inventory.csv',
            mime='text/csv'
        )
    else:
        st.warning("No valid card data found.")
