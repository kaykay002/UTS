import streamlit as st
import pandas as pd
from datetime import date, timedelta
import folium
from streamlit_folium import folium_static

# Load CSV data
distance_df = pd.read_csv('rajasthan_distance.csv')
bus_df = pd.read_csv('rajasthan_buses.csv')
train_df = pd.read_csv('rajasthan_trains.csv')
metro_df = pd.read_csv('rajasthan_metros.csv')
district_df=pd.read_csv("rajasthan_districts.csv")

# Function to get route details (duration, fare, start time)
def get_route_details(df, start, end, mode):
    if mode == "Bus":
        route_df = bus_df
    elif mode == "Train":
        route_df = train_df
    else:
        route_df = metro_df
    
    route = route_df[(route_df['start_city'] == start) & (route_df['end_city'] == end)]
    if not route.empty:
        fare = route['fare'].values[0]
        duration = route['duration_hr'].values[0]
        start_time = route['departure_time'].values[0]
        return fare, duration, start_time
    else:
        return None, None, None

# Function to suggest the optimal route
def suggest_optimal_route(start, end, preferred_modes, intermediate=None):
    if intermediate:
        # Calculate for two legs
        routes = []
        for mode1 in preferred_modes:
            leg1 = get_route_details(bus_df if mode1 == "Bus" else train_df if mode1 == "Train" else metro_df, start, intermediate, mode1)
            if leg1[1] is not None:
                for mode2 in preferred_modes:
                    leg2 = get_route_details(bus_df if mode2 == "Bus" else train_df if mode2 == "Train" else metro_df, intermediate, end, mode2)
                    if leg2[1] is not None:
                        routes.append((mode1, mode2, leg1[1] + leg2[1], leg1[0] + leg2[0], leg1[2], leg2[2]))
        
        # Find the optimal route
        optimal_route = min(routes, key=lambda x: x[2]) if routes else None
        
    else:
        # Calculate for direct journey
        routes = []
        for mode in preferred_modes:
            direct = get_route_details(bus_df if mode == "Bus" else train_df if mode == "Train" else metro_df, start, end, mode)
            if direct[1] is not None:
                routes.append((mode, direct[1], direct[0], direct[2]))
        
        # Find the optimal route
        optimal_route = min(routes, key=lambda x: x[1]) if routes else None
    
    return optimal_route, routes

# Initialize session state
if 'page' not in st.session_state:
    st.session_state['page'] = 'Find Routes'
if 'journey_details' not in st.session_state:
    st.session_state['journey_details'] = None
if 'passenger_details' not in st.session_state:
    st.session_state['passenger_details'] = None

# Page navigation
def navigate_to(page):
    st.session_state['page'] = page

# Main content based on user input
st.title('Universal Ticketing System - Rajasthan')

if st.session_state['page'] == 'Find Routes':
    st.sidebar.title("Transport Finder")
    preferred_modes = st.sidebar.multiselect(
        "Select Preferred Modes of Transport",
        ["Bus", "Train", "Metro"],
        default=["Bus", "Train", "Metro"]
    )

    st.sidebar.subheader("Select Journey Details")
    start_city = st.sidebar.selectbox("Select Start City", distance_df['start_city'].unique())
    end_city = st.sidebar.selectbox("Select End City", distance_df['end_city'].unique())
    intermediate_city = st.sidebar.selectbox("Select Intermediate City (Optional)", ['None'] + list(distance_df['start_city'].unique()))
    journey_date = st.sidebar.date_input("Select Journey Date", date.today())
    return_trip = st.sidebar.checkbox("Round Trip")
    return_date = None
    if return_trip:
        return_date = st.sidebar.date_input("Select Return Date", date.today() + timedelta(days=1))

    # Show the map on the main page before the route details
    st.header("Rajasthan Route Map")
    selected_cities = st.multiselect('Select cities to book ticket between:', district_df['city'].tolist())

    map_center = [26.9124, 75.7873]  # Jaipur, Rajasthan as center
    folium_map = folium.Map(location=map_center, zoom_start=6)

    # Add markers for main cities in Rajasthan
    cities = district_df['city'].unique()
    for city in cities:
        coordinates = district_df[district_df['city'] == city][['latitude', 'longitude']].values[0]
        folium.CircleMarker(
        location=coordinates,
        radius=2,  
        tooltip=city,
        popup=city,
        color='blue',
        fill=True,
        fill_color='blue'
    ).add_to(folium_map)
    
    if len(selected_cities) >= 2:
        for i in range(len(selected_cities) - 1):
            city1 = selected_cities[i]
            city2 = selected_cities[i + 1]
            coordinates1 = district_df[district_df['city'] == city1][['latitude', 'longitude']].values[0]
            coordinates2 = district_df[district_df['city'] == city2][['latitude', 'longitude']].values[0]
            folium.PolyLine([coordinates1, coordinates2], color='red', weight=2.5, opacity=1).add_to(folium_map)


    folium_static(folium_map)

    if start_city and end_city:
        st.header(f"Transport Options from {start_city} to {end_city}")
        st.write(f"Journey Date: {journey_date}")
        
        if intermediate_city != 'None':
            st.subheader(f"Journey via {intermediate_city}")
            
            # Suggest optimal route and other possible routes
            optimal_route, routes = suggest_optimal_route(start_city, end_city, preferred_modes, intermediate_city)
            if optimal_route:
                st.markdown(f"**Optimal Route:** {optimal_route[0]} to {intermediate_city}, then {optimal_route[1]} to {end_city}")
                st.markdown(f"**Total Duration:** {optimal_route[2]} Hours ")
                st.markdown(f"**Total Fare:** ₹{optimal_route[3]:.2f}")
                st.markdown(f"**Start Time:** {optimal_route[4]} (from {start_city} to {intermediate_city}), {optimal_route[5]} (from {intermediate_city} to {end_city})")
                
                # Display other possible routes
                st.write("Other Possible Routes:")
                for route in routes:
                    with st.expander(f"Route: {route[0]} to {intermediate_city}, then {route[1]} to {end_city}"):
                        st.write(f"Total Duration: {route[2]} Hours")
                        st.write(f"Total Fare: ₹{route[3]:.2f}")
                        st.write(f"Start Time: {route[4]} (from {start_city} to {intermediate_city}), {route[5]} (from {intermediate_city} to {end_city})")
                        if st.button(f"Select Route: {route[0]} to {intermediate_city}, then {route[1]} to {end_city}", key=f"route_{route[0]}_{route[1]}"):
                            st.session_state['journey_details'] = {
                                'start_city': start_city,
                                'end_city': end_city,
                                'intermediate_city': intermediate_city,
                                'journey_date': journey_date,
                                'return_trip': return_trip,
                                'return_date': return_date,
                                'selected_route': route,
                            }
                            navigate_to('Passenger Details')
                
            else:
                st.error("No valid routes found for the selected journey.")
                
        else:
            st.subheader("Direct Journey")
            
            # Suggest optimal route and other possible routes
            optimal_route, routes = suggest_optimal_route(start_city, end_city, preferred_modes)
            if optimal_route:
                st.markdown(f"**Optimal Route:** {optimal_route[0]}")
                st.markdown(f"**Total Duration:** {optimal_route[1]} Hours")
                st.markdown(f"**Total Fare:** ₹{optimal_route[2]:.2f}")
                st.markdown(f"**Start Time:** {optimal_route[3]}")
                
                # Display other possible routes
                st.write("Other Possible Routes:")
                for route in routes:
                    with st.expander(f"Route: {route[0]}"):
                        st.write(f"Total Duration: {route[1]} Hours")
                        st.write(f"Total Fare: ₹{route[2]:.2f}")
                        st.write(f"Start Time: {route[3]}")
                        if st.button(f"Select Route: {route[0]}", key=f"route_{route[0]}"):
                            st.session_state['journey_details'] = {
                                'start_city': start_city,
                                'end_city': end_city,
                                'intermediate_city': None,
                                'journey_date': journey_date,
                                'return_trip': return_trip,
                                'return_date': return_date,
                                'selected_route': route,
                            }
                            navigate_to('Passenger Details')
        
        # Return trip details
        if return_trip:
            st.subheader(f"Return Journey from {end_city} to {start_city}")
            st.write(f"Return Date: {return_date}")
            
            if intermediate_city != 'None':
                st.subheader(f"Journey via {intermediate_city}")
                
                # Suggest optimal route and other possible routes
                optimal_route, routes = suggest_optimal_route(end_city, start_city, preferred_modes, intermediate_city)
                if optimal_route:
                    st.markdown(f"**Optimal Route:** {optimal_route[0]} to {intermediate_city}, then {optimal_route[1]} to {start_city}")
                    st.markdown(f"**Total Duration:** {optimal_route[2]} Hours")
                    st.markdown(f"**Total Fare:** ₹{optimal_route[3]:.2f}")
                    st.markdown(f"**Start Time:** {optimal_route[4]} (from {end_city} to {intermediate_city}), {optimal_route[5]} (from {intermediate_city} to {start_city})")
                    
                    # Display other possible routes
                    st.write("Other Possible Routes:")
                    for route in routes:
                        with st.expander(f"Route: {route[0]} to {intermediate_city}, then {route[1]} to {start_city}"):
                            st.write(f"Total Duration: {route[2]} Hours")
                            st.write(f"Total Fare: ₹{route[3]:.2f}")
                            st.write(f"Start Time: {route[4]} (from {end_city} to {intermediate_city}), {route[5]} (from {intermediate_city} to {start_city})")
                            if st.button(f"Select Route: {route[0]} to {intermediate_city}, then {route[1]} to {start_city}", key=f"return_route_{route[0]}_{route[1]}"):
                                st.session_state['return_journey_details'] = {
                                    'start_city': end_city,
                                    'end_city': start_city,
                                    'intermediate_city': intermediate_city,
                                    'journey_date': return_date,
                                    'selected_route': route,
                                }
                                navigate_to('Passenger Details')
                
                else:
                    st.error("No valid routes found for the return journey.")
                    
            else:
                st.subheader("Direct Journey")
                
                # Suggest optimal route and other possible routes
                optimal_route, routes = suggest_optimal_route(end_city, start_city, preferred_modes)
                if optimal_route:
                    st.markdown(f"**Optimal Route:** {optimal_route[0]}")
                    st.markdown(f"**Total Duration:** {optimal_route[1]} Hours")
                    st.markdown(f"**Total Fare:** ₹{optimal_route[2]:.2f}")
                    st.markdown(f"**Start Time:** {optimal_route[3]}")
                    
                    # Display other possible routes
                    st.write("Other Possible Routes:")
                    for route in routes:
                        with st.expander(f"Route: {route[0]}"):
                            st.write(f"Total Duration: {route[1]} Hours")
                            st.write(f"Total Fare: ₹{route[2]:.2f}")
                            st.write(f"Start Time: {route[3]}")
                            if st.button(f"Select Route: {route[0]}", key=f"return_route_{route[0]}"):
                                st.session_state['return_journey_details'] = {
                                    'start_city': end_city,
                                    'end_city': start_city,
                                    'intermediate_city': None,
                                    'journey_date': return_date,
                                    'selected_route': route,
                                }
                                navigate_to('Passenger Details')

elif st.session_state['page'] == 'Passenger Details':
    st.header("Passenger Details")

    # Collect passenger details
    passenger_name = st.text_input("Passenger Name")
    passenger_age = st.number_input("Passenger Age", min_value=0, max_value=120)
    passenger_contact = st.text_input("Contact Number")
    num_seats = st.number_input("Number of Seats", min_value=1, max_value=10)

    if st.button("Submit Passenger Details"):
        st.session_state['passenger_details'] = {
            'name': passenger_name,
            'age': passenger_age,
            'contact': passenger_contact,
            'num_seats': num_seats
        }
        st.success("Passenger details submitted! Proceed to payment.")
        navigate_to('Payment')

elif st.session_state['page'] == 'Payment':
    st.header("Payment Details")

    # Payment integration (simulated)
    payment_option = st.selectbox("Select Payment Method", ["Credit Card", "Debit Card"])
    card_number = st.text_input("Card Number")
    card_expiry = st.text_input("Card Expiry Date (MM/YY)")
    card_cvv = st.text_input("CVV")
    
    if st.button("Proceed to Payment"):
        st.success("Payment Successful!")
        st.balloons()
        st.session_state['page'] = 'Ticket Details'

elif st.session_state['page'] == 'Ticket Details':
    st.header("Booking Confirmation")

    
    # Display journey details
    def display_ticket():
        if 'journey_details' in st.session_state:
            journey_details = st.session_state['journey_details']
            passenger_details = st.session_state.get('passenger_details', {})

            col1,col2=st.columns(2)
            with col1:
                st.markdown('<div class="ticket">', unsafe_allow_html=True)
                st.markdown('<div class="ticket-details">', unsafe_allow_html=True)
                st.subheader("Journey Details")
                st.markdown(f"**From:** {journey_details['selected_route'][0]} from {journey_details['start_city']} at {journey_details['selected_route'][4]}")
                st.markdown(f"**To:** {journey_details['end_city']}")
                if 'intermediate_city' in journey_details and journey_details['intermediate_city']:
                    st.markdown(f"**Via:** {journey_details['selected_route'][1]} from {journey_details['intermediate_city']} at {journey_details['selected_route'][5]}")
                st.markdown(f"**On:** {journey_details['journey_date']}")
                if 'return_trip' in journey_details and journey_details['return_trip']:
                    st.markdown(f"**Return Date:** {journey_details['return_date']}")
                st.markdown(f"**Total Duration:** {int(journey_details['selected_route'][2])} Hours {int(journey_details['selected_route'][2] % 60)} Minutes")
                st.markdown(f"**Total Fare:** ₹{journey_details['selected_route'][3]:.2f}")
            
            with col2:
                if passenger_details:
                    st.markdown('<div class="passenger-details">', unsafe_allow_html=True)
                    st.subheader('Passenger Details')
                    st.markdown(f"**Passenger Name:** {passenger_details['name']}")
                    st.markdown(f"**Passenger Age:** {passenger_details['age']}")
                    st.markdown(f"**Contact Number:** {passenger_details['contact']}")
                    st.markdown(f"**Number of Seats:** {passenger_details['num_seats']}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

    display_ticket()


    
    if st.button("Book Another Ticket"):
        st.session_state['page'] = 'Find Routes'
        st.session_state['journey_details'] = None
        st.session_state['passenger_details'] = None

else:
    st.error("Please select at least one mode of transport.")