# prompts.py

# Prompt to suggest types of trips
TRIP_TYPE_PROMPT = """
Based on the following user preferences:
- Budget: {budget}
- Time frame: {start_date} to {end_date}
- Travelers: {adults} adults, {children} children
- User's initial idea for trip type: "{trip_idea}"
- Starting destination: {start_dest}

Suggest 3 distinct types of trips that would be suitable.
For each suggested trip type, provide:
1. A concise name for the trip type (e.g., "Relaxing Beach Getaway", "Cultural City Exploration", "Adventure Mountain Trek").
2. A brief (1-2 sentences) explanation of why this trip type fits the user's preferences.

Format your response strictly as a JSON list of objects, where each object has a "name" and "explanation" key.
Example:
[
    {{"name": "Relaxing Beach Getaway", "explanation": "This fits your budget and desire for relaxation, offering sunny beaches and calm activities suitable for the whole family."}},
    {{"name": "Historical City Tour", "explanation": "Given your interest in history and a moderate budget, exploring cities with rich pasts could be very engaging."}}
]
"""

# Prompt to suggest cities to visit
CITIES_PROMPT = """
User preferences:
- Budget: {budget}
- Time frame: {start_date} to {end_date}
- Travelers: {adults} adults, {children} children
- Starting destination: {start_dest}
- Confirmed trip type: "{selected_trip_type}"
- Cities user already wants to visit: {initial_cities}

Suggest 3-5 additional cities that align with these preferences.
For each city, provide:
1. City name.
2. A brief (1-2 sentences) reason why it's a good fit for the selected trip type and other preferences.

Consider proximity or logical travel routes from the starting destination if applicable, but prioritize suitability.
Avoid suggesting cities already listed in '{initial_cities}' unless you can provide a very compelling new angle for them.

Format your response strictly as a JSON list of objects, where each object has a "city_name" and "reason" key.
Example:
[
    {{"city_name": "Rome", "reason": "Perfect for a '{selected_trip_type}', offering ancient ruins and vibrant culture within your budget."}},
    {{"city_name": "Kyoto", "reason": "Aligns with a '{selected_trip_type}' by showcasing serene temples and beautiful gardens."}}
]
"""

# Prompt to suggest attractions to visit
ATTRACTIONS_PROMPT = """
User preferences:
- Confirmed trip type: "{selected_trip_type}"
- Selected cities for the trip: {selected_cities_list}
- Travelers: {adults} adults, {children} children (consider age-appropriateness if children > 0)
- Attractions user already wants to visit: {initial_attractions}

For each city in the list {selected_cities_list}, suggest 2-3 relevant attractions.
Provide the attraction name and a short (1-sentence) description highlighting its relevance to the trip type or user profile.
Avoid suggesting attractions already listed in '{initial_attractions}' for those cities.

Format your response strictly as a JSON object where keys are city names (exactly as provided in selected_cities_list),
and values are lists of attraction objects. Each attraction object should have "attraction_name" and "description" keys.
Example:
{{
    "Paris": [
        {{"attraction_name": "Eiffel Tower", "description": "Iconic landmark offering panoramic views, great for any '{selected_trip_type}'."}},
        {{"attraction_name": "Louvre Museum", "description": "Home to world-famous art, ideal for cultural exploration."}}
    ],
    "Kyoto": [
        {{"attraction_name": "Kinkaku-ji (Golden Pavilion)", "description": "A stunning Zen Buddhist temple, reflecting tranquility."}},
        {{"attraction_name": "Fushimi Inari Shrine", "description": "Famous for its thousands of vibrant red torii gates, a unique cultural experience."}}
    ]
}}
"""

# Prompt to suggest restaurants (optional)
RESTAURANTS_PROMPT = """
User preferences:
- Selected cities for the trip: {selected_cities_list}
- Confirmed trip type: "{selected_trip_type}"
- Budget indication: {budget} (use this to infer general price range)
- Travelers: {adults} adults, {children} children

For each city in {selected_cities_list}, suggest 1-2 restaurant options that might appeal to the travelers.
For each restaurant, provide:
1. Name
2. Cuisine type (e.g., Italian, Local, Seafood)
3. Estimated price range (e.g., $, $$, $$$ - relative to the budget indication)
4. A brief (1-sentence) description or why it's recommended for this group/trip type.

Format your response strictly as a JSON object similar to the attractions format: keys are city names,
and values are lists of restaurant objects. Each restaurant object should have "restaurant_name", "cuisine_type", "price_range", and "description" keys.
Example:
{{
    "Rome": [
        {{
            "restaurant_name": "Trattoria Da Enzo al 29",
            "cuisine_type": "Roman, Italian",
            "price_range": "$$",
            "description": "Authentic Roman dishes in a charming Trastevere setting, great for experiencing local flavors."
        }}
    ],
    "Barcelona": [
        {{
            "restaurant_name": "Can Cisa/Bar Brutal",
            "cuisine_type": "Natural Wine Bar, Tapas",
            "price_range": "$$",
            "description": "Excellent selection of natural wines and delicious tapas, suitable for a lively evening."
        }}
    ]
}}
"""

# Prompt to structure the final plan into a day-by-day itinerary
ITINERARY_STRUCTURE_PROMPT = """
Given the following travel components:
- Trip Duration: {num_days} days (from {start_date} to {end_date})
- Selected Cities: {selected_cities_list_str}
- Selected Attractions per city: {attractions_data_str}
- Selected Restaurants per city (if any): {restaurants_data_str}
- Confirmed Trip Type: "{selected_trip_type}"
- Travelers: {adults} adults, {children} children

Create a suggested day-by-day itinerary.
Distribute the selected cities and attractions logically across the {num_days} days.
If multiple cities are selected, allocate a reasonable number of days to each based on the trip duration.
For each day, list:
- Day Number (e.g., Day 1, Day 2)
- Location (City for the day)
- Morning Activity/Attraction (from selected attractions)
- Afternoon Activity/Attraction (from selected attractions)
- Evening Meal Suggestion (from selected restaurants if available for that city, otherwise suggest "Local dining exploration")
- Brief notes or travel tips for the day (e.g., "Book tickets in advance for X", "Allow travel time between Y and Z").

Ensure the itinerary flows well. If there are many attractions for a city, pick the highlights or suggest options.
If the number of days is too short for all selected cities/attractions, prioritize or suggest focusing on a subset, and mention this in a general note at the beginning or end of the itinerary.

Format the output strictly as a JSON object containing two keys: "itinerary_days" and "general_notes".
"itinerary_days" should be a list of day objects. Each day object should have "day_number", "location", "morning_activity", "afternoon_activity", "evening_meal", and "notes" keys.
"general_notes" should be a string for any overall comments (e.g., "This is a packed itinerary, consider...").

Example:
{{
    "general_notes": "This itinerary provides a mix of cultural sites and leisure. Remember to check opening hours for attractions.",
    "itinerary_days": [
        {{
            "day_number": "Day 1",
            "location": "Paris",
            "morning_activity": "Eiffel Tower visit",
            "afternoon_activity": "Louvre Museum tour",
            "evening_meal": "Dinner at Le Petit Chef (example)",
            "notes": "Book Eiffel Tower tickets online to save time. Wear comfortable shoes for the Louvre."
        }},
        {{
            "day_number": "Day 2",
            "location": "Paris",
            "morning_activity": "Seine River Cruise",
            "afternoon_activity": "Explore Montmartre",
            "evening_meal": "Local dining exploration in Montmartre",
            "notes": "The river cruise offers great photo opportunities. Montmartre is hilly."
        }}
    ]
}}
"""

# Prompt for adjusting the plan based on user request
ADJUST_PLAN_PROMPT = """
Here is the current travel plan (in JSON format):
{current_plan_json}

The user wants to make the following adjustment:
"{user_request}"

Please provide an updated travel plan in the exact same JSON format as the original (with "general_notes" and "itinerary_days" keys, and the same structure for day objects).
Incorporate the user's request into the itinerary.
- If the request is to add something, try to fit it in logically.
- If the request is to remove something, remove it.
- If the request is to change duration in a city, adjust the days and activities.
- If the request is vague (e.g., "make it more relaxing"), try to interpret it by perhaps reducing activities per day or adding more free time, and explain the change in the "general_notes".
- If the request is impossible or unclear, explain why in the "general_notes" and return the original plan if no sensible modification can be made.

Updated Plan:
"""
