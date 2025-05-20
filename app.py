import streamlit as st
from datetime import date, timedelta
import json # For displaying plan structure if needed

# Import functions from other files
from llm_handler import get_gemini_response
from prompts import (
    TRIP_TYPE_PROMPT, CITIES_PROMPT, ATTRACTIONS_PROMPT,
    RESTAURANTS_PROMPT, ITINERARY_STRUCTURE_PROMPT, ADJUST_PLAN_PROMPT
)

# --- Page Configuration ---
st.set_page_config(page_title="AI Travel Agent", layout="wide", initial_sidebar_state="expanded")

# --- Initialize Session State ---
# This function ensures all necessary keys are in session_state
def initialize_session_state():
    default_trip_type_description = "e.g., Relaxing beach holiday for a couple"
    default_values = {
        "stage": "initial_input",
        "user_inputs": {
            "starting_destination": "", "budget": 1000.0,
            "time_frame_start": date.today(),
            "time_frame_end": date.today() + timedelta(days=7),
            "num_adults": 1, "num_children": 0,
            "trip_type_description": default_trip_type_description, # Default placeholder
            "cities_to_visit_initial": "", "attractions_to_visit_initial": "",
            "selected_trip_type": None, "selected_cities": [],
            "selected_attractions": {}, "include_restaurants": False,
            "selected_restaurants": {}
        },
        "llm_suggestions": {
            "trip_types": [], "cities": [], "attractions": {}, "restaurants": {}
        },
        "travel_plan_raw": None, # For the structured itinerary from LLM
        "travel_plan_text_adjustment": "", # For user text input to adjust plan
        "error_message": None,
        "show_debug": False, # Toggle for showing debug info
        "default_trip_type_placeholder": default_trip_type_description # Store placeholder for comparison
    }
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Ensure nested dictionaries are also initialized if outer key exists but inner is missing
    if 'user_inputs' in st.session_state:
        for k, v in default_values['user_inputs'].items():
            if k not in st.session_state.user_inputs:
                st.session_state.user_inputs[k] = v
    if 'llm_suggestions' in st.session_state:
        for k, v in default_values['llm_suggestions'].items():
            if k not in st.session_state.llm_suggestions:
                st.session_state.llm_suggestions[k] = v

initialize_session_state()

# --- Helper Functions ---
def reset_to_stage(stage_name):
    """Resets relevant parts of session state when going back to a previous stage."""
    st.session_state.stage = stage_name
    if stage_name == "initial_input":
        # Preserve some initial inputs if desired, or full reset:
        current_trip_desc = st.session_state.user_inputs.get("trip_type_description")
        initialize_session_state() # Full reset
        # Optionally restore some fields if you want them to persist after full reset
        # st.session_state.user_inputs["trip_type_description"] = current_trip_desc

    elif stage_name == "suggest_trip_type":
        st.session_state.llm_suggestions['trip_types'] = []
        st.session_state.user_inputs['selected_trip_type'] = None
        st.session_state.llm_suggestions['cities'] = []
        st.session_state.user_inputs['selected_cities'] = []
        st.session_state.llm_suggestions['attractions'] = {}
        st.session_state.user_inputs['selected_attractions'] = {}
        st.session_state.llm_suggestions['restaurants'] = {}
        st.session_state.user_inputs['selected_restaurants'] = {}
        st.session_state.travel_plan_raw = None
    elif stage_name == "suggest_cities":
        st.session_state.llm_suggestions['cities'] = []
        st.session_state.user_inputs['selected_cities'] = []
        st.session_state.llm_suggestions['attractions'] = {}
        st.session_state.user_inputs['selected_attractions'] = {}
        st.session_state.llm_suggestions['restaurants'] = {}
        st.session_state.user_inputs['selected_restaurants'] = {}
        st.session_state.travel_plan_raw = None
    # Add more specific resets if needed for other stages

def calculate_num_days(start_date, end_date):
    if start_date and end_date and start_date <= end_date:
        return (end_date - start_date).days + 1
    return 0

# --- Sidebar for Navigation/Debug ---
with st.sidebar:
    st.title("AI Travel Agent ✈️")
    st.write("Your personal trip planner.")

    if st.button("Start Over / New Trip"):
        reset_to_stage("initial_input")
        st.rerun()

    st.markdown("---")
    st.session_state.show_debug = st.checkbox("Show Debug Info", value=st.session_state.get("show_debug", False))
    if st.session_state.show_debug:
        st.subheader("Debug Info:")
        st.write("Current Stage:", st.session_state.stage)
        st.write("User Inputs:", st.session_state.user_inputs)
        # st.write("LLM Suggestions:", st.session_state.llm_suggestions) # Can be verbose
        st.write("Travel Plan Raw:", st.session_state.travel_plan_raw)


# --- Main Application Logic ---

# Stage 0: Initial User Inputs
if st.session_state.stage == "initial_input":
    st.header("🌍 1. Tell Us About Your Dream Trip")
    with st.form("initial_trip_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.user_inputs['starting_destination'] = st.text_input(
                "Starting Destination",
                st.session_state.user_inputs.get('starting_destination', "London, UK")
            )
            st.session_state.user_inputs['budget'] = st.number_input(
                "Budget (e.g., in USD)",
                min_value=0.0, value=st.session_state.user_inputs.get('budget', 1000.0), format="%.2f"
            )
            st.session_state.user_inputs['time_frame_start'] = st.date_input(
                "Trip Start Date",
                value=st.session_state.user_inputs.get('time_frame_start', date.today())
            )
            st.session_state.user_inputs['time_frame_end'] = st.date_input(
                "Trip End Date",
                value=st.session_state.user_inputs.get('time_frame_end', date.today() + timedelta(days=7))
            )
        with c2:
            st.session_state.user_inputs['num_adults'] = st.number_input(
                "Number of Adults",
                min_value=1, step=1, value=st.session_state.user_inputs.get('num_adults', 1)
            )
            st.session_state.user_inputs['num_children'] = st.number_input(
                "Number of Children",
                min_value=0, step=1, value=st.session_state.user_inputs.get('num_children', 0)
            )
            # Use a unique key for the text_area to ensure its state is managed correctly by Streamlit
            trip_type_description_input = st.text_area(
                "Describe your ideal type of trip (leave as default or empty to get AI suggestions)",
                value=st.session_state.user_inputs.get('trip_type_description', st.session_state.default_trip_type_placeholder),
                height=100,
                key="trip_type_description_input_key" # Unique key
            )
            st.session_state.user_inputs['trip_type_description'] = trip_type_description_input


        st.session_state.user_inputs['cities_to_visit_initial'] = st.text_area(
            "Cities you definitely want to visit (optional, comma-separated)",
            value=st.session_state.user_inputs.get('cities_to_visit_initial', "")
        )
        st.session_state.user_inputs['attractions_to_visit_initial'] = st.text_area(
            "Attractions you definitely want to visit (optional, comma-separated)",
            value=st.session_state.user_inputs.get('attractions_to_visit_initial', "")
        )

        submitted_initial = st.form_submit_button("Next Step ➡️")

    if submitted_initial:
        if not st.session_state.user_inputs['starting_destination']:
            st.error("Please enter a starting destination.")
        elif st.session_state.user_inputs['time_frame_start'] > st.session_state.user_inputs['time_frame_end']:
            st.error("Trip end date must be after or the same as the start date.")
        else:
            user_provided_trip_type = st.session_state.user_inputs['trip_type_description']
            # Check if user provided a specific trip type (not empty and not the placeholder)
            if user_provided_trip_type and user_provided_trip_type.strip() != "" and user_provided_trip_type != st.session_state.default_trip_type_placeholder:
                st.session_state.user_inputs['selected_trip_type'] = user_provided_trip_type
                st.session_state.stage = "suggest_cities" # Skip to city suggestions
                st.session_state.llm_suggestions['cities'] = [] # Clear previous city suggestions
                st.success(f"Using your specified trip type: {user_provided_trip_type}")
            else:
                st.session_state.stage = "suggest_trip_type" # Go to AI trip type suggestions
                st.session_state.llm_suggestions['trip_types'] = [] # Clear previous suggestions
            st.rerun()

# Stage 1: Suggest Type of Trip (This stage is now potentially skippable)
elif st.session_state.stage == "suggest_trip_type":
    st.header("💡 2. AI Suggested Trip Types")
    st.info("Since you didn't specify a particular trip type, here are some AI suggestions based on your inputs.")
    ui = st.session_state.user_inputs

    if not st.session_state.llm_suggestions.get('trip_types'): # Fetch only if not already fetched
        prompt = TRIP_TYPE_PROMPT.format(
            budget=ui['budget'], start_date=ui['time_frame_start'].isoformat(),
            end_date=ui['time_frame_end'].isoformat(), adults=ui['num_adults'],
            children=ui['num_children'], trip_idea=ui.get('trip_type_description', 'any'), # Use 'any' if it was placeholder
            start_dest=ui['starting_destination']
        )
        with st.spinner("AI is brainstorming trip types..."):
            suggestions = get_gemini_response(prompt, expect_json=True)
        if suggestions and isinstance(suggestions, list) and len(suggestions) > 0:
            st.session_state.llm_suggestions['trip_types'] = suggestions
        else:
            st.error("Could not get trip type suggestions. Please try adjusting your inputs or try again later.")
            if st.button("Try Again to Get Trip Types"): st.rerun() # Allow retry

    trip_type_suggestions = st.session_state.llm_suggestions.get('trip_types', [])
    if trip_type_suggestions:
        options = [f"{tt['name']} – {tt['explanation']}" for tt in trip_type_suggestions]
        
        # Determine current selection for radio button
        current_selection_index = 0 # Default to first option
        if ui.get('selected_trip_type'):
            try:
                # Find index of currently selected trip type if it exists in suggestions
                current_selection_index = [opt.startswith(ui['selected_trip_type']) for opt in options].index(True)
            except ValueError:
                current_selection_index = 0 # Default if not found

        selected_option_display = st.radio(
            "Which type of trip sounds best?", options,
            index=current_selection_index,
            key="trip_type_radio_selection"
        )
        # Extract the name part for storing
        if selected_option_display:
            st.session_state.user_inputs['selected_trip_type'] = selected_option_display.split(" – ")[0]

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("⬅️ Back to Initial Inputs"):
            reset_to_stage("initial_input")
            st.rerun()
    with col2:
        # Enable "Next" button if suggestions are loaded and a selection is made
        if trip_type_suggestions and st.session_state.user_inputs.get('selected_trip_type'):
            if st.button("Next: Suggest Cities ➡️"):
                st.session_state.stage = "suggest_cities"
                st.session_state.llm_suggestions['cities'] = [] # Clear previous city suggestions
                st.rerun()
        elif not trip_type_suggestions:
             st.warning("Waiting for or unable to generate trip type suggestions. You can go back to provide your own trip type.")


# Stage 2: Suggest Cities
elif st.session_state.stage == "suggest_cities":
    st.header("🏙️ 3. Suggested Cities to Visit")
    ui = st.session_state.user_inputs

    if not ui.get('selected_trip_type'):
        st.warning("No trip type selected or provided. Please go back to the initial inputs or select a trip type.")
        if st.button("⬅️ Back to Initial Inputs (to specify trip type)"):
            reset_to_stage("initial_input") # Go all the way back if no trip type
            st.rerun()
        st.stop()
    
    st.info(f"Selected trip type: **{ui['selected_trip_type']}**")


    if not st.session_state.llm_suggestions.get('cities'):
        prompt = CITIES_PROMPT.format(
            budget=ui['budget'], start_date=ui['time_frame_start'].isoformat(),
            end_date=ui['time_frame_end'].isoformat(), adults=ui['num_adults'],
            children=ui['num_children'], start_dest=ui['starting_destination'],
            selected_trip_type=ui['selected_trip_type'],
            initial_cities=ui.get('cities_to_visit_initial', 'None')
        )
        with st.spinner(f"AI is finding cities for a {ui['selected_trip_type'].lower()}..."):
            suggestions = get_gemini_response(prompt, expect_json=True)
        if suggestions and isinstance(suggestions, list):
            st.session_state.llm_suggestions['cities'] = suggestions
        else:
            st.error("Could not get city suggestions. Please try again later.")

    city_suggestions = st.session_state.llm_suggestions.get('cities', [])
    all_city_options = []
    # Add initially specified cities first
    if ui.get('cities_to_visit_initial'):
        initial_cities_list = [city.strip() for city in ui['cities_to_visit_initial'].split(',') if city.strip()]
        all_city_options.extend(initial_cities_list)

    if city_suggestions:
        st.write("AI suggests these additional cities based on your preferences:")
        for city_sugg in city_suggestions:
            st.markdown(f"- **{city_sugg['city_name']}**: {city_sugg['reason']}")
            if city_sugg['city_name'] not in all_city_options: # Avoid duplicates
                 all_city_options.append(city_sugg['city_name'])
    elif not all_city_options: # Only show this if no initial cities AND no AI suggestions
        st.write("No additional cities suggested by AI. You can proceed with your initial list if any.")

    if not all_city_options:
        st.warning("No cities to select. Please provide initial cities or let the AI suggest some if the previous step was skipped.")
    else:
        # Ensure unique options for multiselect
        unique_all_city_options = list(dict.fromkeys(all_city_options))
        st.session_state.user_inputs['selected_cities'] = st.multiselect(
            "Select the cities you'd like to include in your plan:",
            options=unique_all_city_options,
            default=st.session_state.user_inputs.get('selected_cities', [])
        )

    col1, col2 = st.columns([1,1])
    with col1:
        # Determine where to go back: to trip type suggestion or initial inputs
        # If selected_trip_type was from AI, go to suggest_trip_type.
        # If user provided it initially, and skipped suggest_trip_type, go to initial_input.
        # For simplicity now, always offer path back to suggest_trip_type if it exists, else initial_input
        # A more robust way would be to track if suggest_trip_type was ever visited.
        # For now, if llm_suggestions.trip_types is populated, that stage was likely visited.
        if st.session_state.llm_suggestions.get('trip_types'):
            if st.button("⬅️ Back to Trip Type Selection"):
                reset_to_stage("suggest_trip_type")
                st.rerun()
        else:
            if st.button("⬅️ Back to Initial Inputs"):
                reset_to_stage("initial_input")
                st.rerun()

    with col2:
        if st.session_state.user_inputs.get('selected_cities'):
            if st.button("Next: Suggest Attractions ➡️"):
                st.session_state.stage = "suggest_attractions"
                st.session_state.llm_suggestions['attractions'] = {} # Clear previous
                st.rerun()
        elif all_city_options:
            st.warning("Please select at least one city to proceed.")


# Stage 3: Suggest Attractions
elif st.session_state.stage == "suggest_attractions":
    st.header("🏰 4. Suggested Attractions")
    ui = st.session_state.user_inputs

    if not ui.get('selected_cities'):
        st.warning("No cities selected. Please go back.")
        if st.button("⬅️ Select Cities"):
            reset_to_stage("suggest_cities")
            st.rerun()
        st.stop()
    
    st.info(f"Getting attractions for: **{', '.join(ui['selected_cities'])}** for a **{ui['selected_trip_type']}** trip.")


    # Fetch if no attractions, or if selected cities have changed since last fetch
    should_fetch_attractions = not st.session_state.llm_suggestions.get('attractions') or \
                               set(st.session_state.llm_suggestions.get('attractions', {}).keys()) != set(ui.get('selected_cities',[]))

    if should_fetch_attractions:
        prompt = ATTRACTIONS_PROMPT.format(
            selected_trip_type=ui['selected_trip_type'],
            selected_cities_list=ui['selected_cities'],
            adults=ui['num_adults'], children=ui['num_children'],
            initial_attractions=ui.get('attractions_to_visit_initial', 'None')
        )
        with st.spinner("AI is finding attractions..."):
            suggestions = get_gemini_response(prompt, expect_json=True)

        if suggestions and isinstance(suggestions, dict):
            st.session_state.llm_suggestions['attractions'] = suggestions
        else:
            st.error("Could not get attraction suggestions. Please try again later.")
            st.session_state.llm_suggestions['attractions'] = {} # Ensure it's a dict

    attraction_suggestions_by_city = st.session_state.llm_suggestions.get('attractions', {})
    current_selected_attractions = ui.get('selected_attractions', {})

    # Initialize selected_attractions structure for newly selected cities
    for city_name in ui['selected_cities']:
        if city_name not in current_selected_attractions:
            current_selected_attractions[city_name] = []

    initial_attractions_list = [att.strip() for att in ui.get('attractions_to_visit_initial', '').split(',') if att.strip()]

    for city_name in ui['selected_cities']:
        st.subheader(f"Attractions in {city_name}:")
        city_attraction_options = []

        # Add user's initial attractions as options
        # This simple version adds all initial attractions to all cities' options.
        # A more complex app might parse city-specific initial attractions.
        for init_att in initial_attractions_list:
            if init_att not in city_attraction_options:
                 city_attraction_options.append(init_att)

        # Add AI suggested attractions
        if city_name in attraction_suggestions_by_city and attraction_suggestions_by_city[city_name]:
            st.write(f"AI suggests for {city_name}:")
            for attr_sugg in attraction_suggestions_by_city[city_name]:
                st.markdown(f"- **{attr_sugg['attraction_name']}**: {attr_sugg['description']}")
                if attr_sugg['attraction_name'] not in city_attraction_options:
                    city_attraction_options.append(attr_sugg['attraction_name'])
        elif not initial_attractions_list : # Only show this if no AI suggestions AND no initial ones for options
            st.write(f"No specific AI suggestions for {city_name}, or suggestions failed.")

        if not city_attraction_options:
            st.write(f"No attraction options available for {city_name}.")
            current_selected_attractions[city_name] = []
        else:
            # Ensure unique options
            unique_city_attraction_options = list(dict.fromkeys(city_attraction_options))
            current_selected_attractions[city_name] = st.multiselect(
                f"Select attractions for {city_name}:",
                options=unique_city_attraction_options,
                default=current_selected_attractions.get(city_name, []),
                key=f"attractions_{city_name.replace(' ','_')}" # Ensure key is valid
            )
    st.session_state.user_inputs['selected_attractions'] = current_selected_attractions

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("⬅️ Back to City Selection"):
            reset_to_stage("suggest_cities")
            st.rerun()
    with col2:
        total_selected_attractions = sum(len(v) for v in current_selected_attractions.values() if isinstance(v, list))
        # Allow proceeding if user selected some, or if there were no options to begin with
        can_proceed = total_selected_attractions > 0 or \
                      (not any(attraction_suggestions_by_city.values()) and not initial_attractions_list)

        if can_proceed:
            if st.button("Next: Restaurant Options ➡️"):
                st.session_state.stage = "suggest_restaurants"
                st.session_state.llm_suggestions['restaurants'] = {} # Clear previous
                st.rerun()
        else:
            st.warning("Please select at least one attraction overall, or ensure AI suggestions have loaded if options were available.")


# Stage 4: Suggest Restaurants (Optional)
elif st.session_state.stage == "suggest_restaurants":
    st.header("🍽️ 5. Restaurant Suggestions (Optional)")
    ui = st.session_state.user_inputs
    st.session_state.user_inputs['include_restaurants'] = st.checkbox(
        "Include restaurant suggestions in the plan?",
        value=st.session_state.user_inputs.get('include_restaurants', False)
    )

    if st.session_state.user_inputs['include_restaurants']:
        if not ui.get('selected_cities'):
            st.warning("No cities selected for restaurant suggestions. Please go back.")
            if st.button("⬅️ Select Cities"): reset_to_stage("suggest_cities"); st.rerun()
            st.stop()

        should_fetch_restaurants = not st.session_state.llm_suggestions.get('restaurants') or \
                                   set(st.session_state.llm_suggestions.get('restaurants', {}).keys()) != set(ui.get('selected_cities',[]))

        if should_fetch_restaurants:
            prompt = RESTAURANTS_PROMPT.format(
                selected_cities_list=ui['selected_cities'],
                selected_trip_type=ui['selected_trip_type'],
                budget=ui['budget'], adults=ui['num_adults'], children=ui['num_children']
            )
            with st.spinner("AI is looking up restaurants..."):
                suggestions = get_gemini_response(prompt, expect_json=True)
            if suggestions and isinstance(suggestions, dict):
                st.session_state.llm_suggestions['restaurants'] = suggestions
            else:
                st.error("Could not get restaurant suggestions.")
                st.session_state.llm_suggestions['restaurants'] = {}

        restaurant_suggestions_by_city = st.session_state.llm_suggestions.get('restaurants', {})
        current_selected_restaurants = ui.get('selected_restaurants', {})

        for city_name in ui['selected_cities']:
            if city_name not in current_selected_restaurants:
                current_selected_restaurants[city_name] = []

            st.subheader(f"Restaurants in {city_name}:")
            city_restaurant_options = []
            # Store full restaurant objects if available, to preserve details
            city_restaurant_details_map = {} 

            if city_name in restaurant_suggestions_by_city and restaurant_suggestions_by_city[city_name]:
                st.write(f"AI suggests for {city_name}:")
                for rest_sugg in restaurant_suggestions_by_city[city_name]:
                    option_label = f"{rest_sugg['restaurant_name']} ({rest_sugg['cuisine_type']}, {rest_sugg['price_range']}) – {rest_sugg['description']}"
                    city_restaurant_options.append(option_label)
                    city_restaurant_details_map[option_label] = rest_sugg # Store full object
            else:
                st.write(f"No AI restaurant suggestions for {city_name}.")

            if not city_restaurant_options:
                st.write(f"No restaurant options available for {city_name}.")
                current_selected_restaurants[city_name] = []
            else:
                # Default selection: if names were stored, find corresponding labels
                default_selection_labels = []
                if current_selected_restaurants.get(city_name):
                    for label in city_restaurant_options:
                        # Assuming stored value is the restaurant name
                        if label.split(" (")[0] in current_selected_restaurants[city_name]:
                            default_selection_labels.append(label)
                
                selected_labels = st.multiselect(
                    f"Select restaurants for {city_name}:",
                    options=city_restaurant_options,
                    default=default_selection_labels,
                    key=f"restaurants_{city_name.replace(' ','_')}"
                )
                # Store the selected restaurant names (or full objects if you prefer more detail later)
                current_selected_restaurants[city_name] = [label.split(" (")[0] for label in selected_labels]
        st.session_state.user_inputs['selected_restaurants'] = current_selected_restaurants

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("⬅️ Back to Attraction Selection"):
            reset_to_stage("suggest_attractions")
            st.rerun()
    with col2:
        if st.button("Generate Travel Plan ✨➡️"):
            st.session_state.stage = "generate_plan"
            st.session_state.travel_plan_raw = None # Clear previous plan
            st.rerun()


# Stage 5: Generate Travel Plan
elif st.session_state.stage == "generate_plan":
    st.header("📝 6. Your AI-Generated Travel Plan")
    ui = st.session_state.user_inputs

    num_days = calculate_num_days(ui['time_frame_start'], ui['time_frame_end'])
    if num_days == 0:
        st.error("Invalid time frame. Please go back and correct the dates.")
        if st.button("⬅️ Back to Initial Inputs"): reset_to_stage("initial_input"); st.rerun()
        st.stop()


    if not st.session_state.travel_plan_raw: # Generate plan only once per this stage entry
        attractions_data_for_prompt = {}
        for city, attrs in ui.get('selected_attractions', {}).items():
            if attrs and city in ui.get('selected_cities', []): # Ensure city is still selected
                attractions_data_for_prompt[city] = [{"attraction_name": attr, "description": "User selected"} for attr in attrs]

        restaurants_data_for_prompt = {}
        if ui.get('include_restaurants', False):
            for city, rests in ui.get('selected_restaurants', {}).items():
                if rests and city in ui.get('selected_cities', []):
                     restaurants_data_for_prompt[city] = [{"restaurant_name": r, "description": "User selected"} for r in rests]

        prompt = ITINERARY_STRUCTURE_PROMPT.format(
            num_days=num_days,
            start_date=ui['time_frame_start'].isoformat(),
            end_date=ui['time_frame_end'].isoformat(),
            selected_cities_list_str=str(ui['selected_cities']),
            attractions_data_str=json.dumps(attractions_data_for_prompt),
            restaurants_data_str=json.dumps(restaurants_data_for_prompt),
            selected_trip_type=ui['selected_trip_type'],
            adults=ui['num_adults'], children=ui['num_children']
        )
        with st.spinner("AI is structuring your itinerary... This might take a moment."):
            plan_output = get_gemini_response(prompt, expect_json=True)

        if plan_output and isinstance(plan_output, dict) and "itinerary_days" in plan_output:
            st.session_state.travel_plan_raw = plan_output
        else:
            st.error("Could not structure the itinerary with AI. Displaying a basic summary of your selections.")
            fallback_plan = {"general_notes": "AI structuring failed. Here's a summary of your selections:", "itinerary_days": []}
            # Create a very basic fallback based on selected items
            for city_idx, city_name in enumerate(ui.get('selected_cities', [])):
                day_entry = {
                    "day_number": f"Focus on {city_name}",
                    "location": city_name,
                    "morning_activity": "Explore attractions: " + ", ".join(ui.get('selected_attractions', {}).get(city_name, ["Not specified"])),
                    "afternoon_activity": "Further exploration or leisure",
                    "evening_meal": "Try local restaurants" + (": " + ", ".join(ui.get('selected_restaurants', {}).get(city_name, [])) if ui.get('include_restaurants') and ui.get('selected_restaurants', {}).get(city_name) else ""),
                    "notes": "This is a basic outline. Adjust as needed."
                }
                fallback_plan["itinerary_days"].append(day_entry)
            if not fallback_plan["itinerary_days"]:
                 fallback_plan["general_notes"] = "No items selected to display in the plan."
            st.session_state.travel_plan_raw = fallback_plan


    plan_data = st.session_state.travel_plan_raw
    if plan_data:
        st.subheader("Trip Overview")
        st.markdown(f"**Trip Type:** {ui.get('selected_trip_type', 'N/A')}")
        st.markdown(f"**Duration:** {num_days} days ({ui['time_frame_start'].strftime('%B %d, %Y')} to {ui['time_frame_end'].strftime('%B %d, %Y')})")
        st.markdown(f"**Travelers:** {ui['num_adults']} Adult(s), {ui['num_children']} Child(ren)")
        st.markdown(f"**Selected Cities:** {', '.join(ui.get('selected_cities', ['N/A']))}")

        if plan_data.get("general_notes"):
            st.info(f"**General Notes from AI:** {plan_data['general_notes']}")

        st.subheader("Daily Itinerary")
        if plan_data.get("itinerary_days"):
            for day_plan in plan_data["itinerary_days"]:
                with st.expander(f"**{day_plan.get('day_number', 'Day X')}**: {day_plan.get('location', 'N/A')}", expanded=True):
                    st.markdown(f"- **Morning:** {day_plan.get('morning_activity', 'N/A')}")
                    st.markdown(f"- **Afternoon:** {day_plan.get('afternoon_activity', 'N/A')}")
                    st.markdown(f"- **Evening Meal:** {day_plan.get('evening_meal', 'N/A')}")
                    if day_plan.get('notes'):
                        st.markdown(f"- *Notes:* {day_plan.get('notes')}")
        else:
            st.write("No daily itinerary structure available.")

        st.markdown("---")
        st.subheader("Adjust Your Plan")
        st.session_state.travel_plan_text_adjustment = st.text_area(
            "What would you like to change? (e.g., 'Add a visit to the National Gallery in London', 'Make Day 2 more relaxing')",
            value=st.session_state.get('travel_plan_text_adjustment', ""), height=100,
            key="plan_adjustment_input"
        )
        if st.button("🤖 Ask AI to Adjust Plan"):
            if st.session_state.travel_plan_text_adjustment and st.session_state.travel_plan_raw:
                adjustment_prompt = ADJUST_PLAN_PROMPT.format(
                    current_plan_json=json.dumps(st.session_state.travel_plan_raw),
                    user_request=st.session_state.travel_plan_text_adjustment
                )
                with st.spinner("AI is attempting to adjust your plan..."):
                    adjusted_plan_output = get_gemini_response(adjustment_prompt, expect_json=True)

                if adjusted_plan_output and isinstance(adjusted_plan_output, dict) and "itinerary_days" in adjusted_plan_output:
                    st.session_state.travel_plan_raw = adjusted_plan_output
                    st.session_state.travel_plan_text_adjustment = "" # Clear input
                    st.success("Plan adjusted by AI!")
                    st.rerun()
                else:
                    st.error("AI could not adjust the plan as requested, or the response was not in the expected format. Please try rephrasing your request or make manual notes.")
            elif not st.session_state.travel_plan_text_adjustment:
                st.warning("Please enter an adjustment request.")
            elif not st.session_state.travel_plan_raw:
                st.warning("No current plan to adjust. Please generate a plan first.")
    else:
        st.info("Your travel plan is being generated or was not successfully created.")

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("⬅️ Back to Restaurant Selection"):
            reset_to_stage("suggest_restaurants")
            st.rerun()
    with col2:
        if st.button("Start a New Trip Planning"):
            reset_to_stage("initial_input")
            st.rerun()


# Fallback for unknown stage
else:
    st.error("Invalid application stage. Resetting to start.")
    reset_to_stage("initial_input")
    st.rerun()



