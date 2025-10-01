import streamlit as st
import pandas as pd
import altair as alt
from difflib import get_close_matches

st.write("App is running with the latest code")

# load data, cached
@st.cache_data
def load_data():
    return pd.read_csv("Airline_Delay_Cause.csv")


# airline fuzzy match with common alternates
def fuzzy_match_airline(user_input, airline_list):
    alternate_lookup = {
        "southwest": "Southwest Airlines",
        "delta": "Delta Air Lines Inc.",
        "american": "American Airlines Inc.",
        "united":"United Air Lines Inc.",
        "alaska": "Alaska Airlines Inc.",
        "spirit": "Spirit Airlines",
    }

    if user_input.lower() in alternate_lookup:
        return alternate_lookup[user_input.lower()]
    
    matches = get_close_matches(user_input, airline_list, n=1, cutoff=0.4)
    if matches:
        return matches[0]
    else:
        return None

# flight stats calculator    
def get_flight_stats(df, airport_code, airline_name):
    filtered = df[
        (df["airport"] == airport_code) &
        (df["carrier_name"] == airline_name)
    ]

    if filtered.empty:
        return None
    
    total_arrivals = filtered["arr_flights"].sum()
    total_delays = filtered["arr_del15"].sum()
    delay_percent = (total_delays / total_arrivals) * 100
    
    return {
        "total_arrivals": int(total_arrivals),
        "total_delays": int(total_delays),
        "delay_percent": round(delay_percent, 2)
    }


def plot_monthly_delays(df, airport_code, airline_name, view_type):
    # filter only rows for specific airline/airport
    monthly = df[
        (df['airport'] == airport_code) &
        (df['carrier_name'] == airline_name)
    ][['year','month', 'arr_flights', 'arr_del15']]

    if monthly.empty:
        st.info("No monthly data available for this combination.")
        return
    
    if view_type == "Average by Month (all years combined)":
    
        # group by month, calculate delay percentage
        monthly = monthly.groupby('month').sum().reset_index()
        monthly['delay_percent'] = (monthly['arr_del15'] / monthly['arr_flights']) * 100

        # create chart
        chart = alt.Chart(monthly).mark_line(point=True).encode(
            x=alt.X('month:O', title='Month'),
            y=alt.Y('delay_percent:Q', title='Delay %'),
            tooltip=['month', 'delay_percent']
        ).properties(
            title=f"{airline_name} Delay % at {airport_code} (Average by Month, {min_year}-{max_year})",
            width=600,
            height=400
        )

    else: # month by month over years
        monthly = monthly.groupby(['year', 'month']).sum().reset_index()
        monthly['delay_percent'] = (monthly['arr_del15'] / monthly['arr_flights']) * 100
        monthly['date'] = pd.to_datetime(
            monthly['year'].astype(str) + '-' + monthly['month'].astype(str) + '-01'
        )

        chart = alt.Chart(monthly).mark_line(point=True).encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('delay_percent:Q', title='Delay %'),
            tooltip=['year', 'month', 'delay_percent']
        ).properties(
            title=f"{airline_name} Delay % at {airport_code} ({min_year}-{max_year}, Monthly Timeline)",
            width=600,
            height=400
        )

    st.altair_chart(chart)
    if view_type == "Average by Month (all years combined)":
        st.caption("Average delay % for each calendar month, across all years in the dataset")
    else:
        st.caption("Delay % trend shown month by month across years")

def plot_delay_cause_pie(df, airport_code, airline_name):
    filtered = df[
        (df['airport'] == airport_code) &
        (df['carrier_name'] == airline_name)
    ]

    if filtered.empty:
        st.info("No data available for delay causes.")
        return
        
    # sum all reasons for delays
    totals = {
        "Carrier Delay": filtered["carrier_delay"].sum(),
        "Weather Delay": filtered["weather_delay"].sum(),
        "NAS Delay": filtered["nas_delay"].sum(),
        "Security Delay": filtered["security_delay"].sum(),
        "Late Aircraft": filtered["late_aircraft_delay"].sum()
    }

    delay_df = pd.DataFrame({
        "Cause": list(totals.keys()),
        "Minutes": list(totals.values())
    })

    # dataframe for plotting
    delay_df = delay_df[delay_df["Minutes"] > 0]

    chart = alt.Chart(delay_df).mark_arc(innerRadius=50).encode(
        theta="Minutes:Q",
        color="Cause:N",
        tooltip=["Cause", "Minutes"]
    ).properties(
        title=f"Delay Causes for {airline_name} at {airport_code}",
        width=400,
        height=400
    )

    st.altair_chart(chart)

#--------------------
# streamlit ui
#--------------------


df = load_data()
min_year = int(df['year'].min())
max_year = int(df['year'].max())

st.title("Flight Delay Tool")
st.caption(f"Data includes flights from **{min_year}** to **{max_year}**")
st.image("plane_wing.jpg", width=250)
st.write("Get historical delay rate information")


all_airlines = df['carrier_name'].unique()

#input
airport_input = st.text_input(
    "Enter an airport code (three letters, like LAX):",
    value=st.session_state.get("airport_input", "")
).upper()

airline_input = st.text_input(
    "Enter an airline name (such as Delta):",
    value=st.session_state.get("airline_input", "")
)
submit = st.button(" Search")

#save search to session state
if submit and airport_input and airline_input:
    st.session_state.airport_input = airport_input
    st.session_state.airline_input = airline_input

# check to make sure both inputs filled
if "airport_input" in st.session_state and "airline_input" in st.session_state:
    matched_airline = fuzzy_match_airline(st.session_state.airline_input, all_airlines)

    if not matched_airline:
        st.error("Could not find a close match for that airline.")
    else:
        st.success(f" Searched airline: **{matched_airline}**")

        stats = get_flight_stats(df, st.session_state.airport_input, matched_airline)

        if not stats:
            st.warning("Nothing found for that airport/airline combination")
        else:
            st.subheader(f"Results for {matched_airline} at {st.session_state.airport_input}")
            st.metric("Total Arrivals", stats["total_arrivals"])
            st.metric("Delayed Flights (15+ min)", stats["total_delays"])
            st.metric("Percent Delayed", f"{stats['delay_percent']}%")


            if "view_type" not in st.session_state:
                st.session_state.view_type = "Average by Month (all years combined)"

            view_type = st.radio(
                "Choose how to view monthly delays:",
                ("Average by Month (all years combined)", "Timeline (month by month over years)"),
                index=0 if st.session_state.view_type == "Average by Month (all years combined)" else 1,
                #save user's view choice in session state
                key="view_type"
            )

            plot_monthly_delays(df, st.session_state.airport_input, matched_airline, view_type)
            plot_delay_cause_pie(df, st.session_state.airport_input, matched_airline)

            if st.button("New Search"):
                st.session_state.clear()
                st.experimental_rerun()
    