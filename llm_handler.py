import streamlit as st
import google.generativeai as genai
import json
import re # For more robust JSON cleaning

# --- Configuration ---
# Model name can be adjusted based on availability and desired capability/cost.
# "gemini-1.5-flash-latest" is often a good balance.
# "gemini-1.5-pro-latest" is more powerful.
DEFAULT_MODEL_NAME = "gemini-2.0-flash"

# Safety settings: Adjust thresholds as needed for your application.
# Blocking too aggressively might prevent useful responses.
DEFAULT_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Generation config: Adjust for desired output characteristics.
DEFAULT_GENERATION_CONFIG = genai.types.GenerationConfig(
    # temperature=0.7,  # Lower for more predictable, higher for more creative
    # max_output_tokens=8192, # Gemini 1.5 Flash has a large context window
    # top_p=0.95,
    # top_k=64
    response_mime_type="application/json" # Crucial for asking for JSON output
)

def configure_gemini():
    """
    Configures the Gemini API with the API key from Streamlit secrets.
    Returns True if configuration is successful, False otherwise.
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        if not api_key:
            st.error("GEMINI_API_KEY is not set in Streamlit secrets. Please add it to .streamlit/secrets.toml")
            return False
        genai.configure(api_key=api_key)
        return True
    except KeyError:
        st.error("GEMINI_API_KEY not found in Streamlit secrets. Please add it to .streamlit/secrets.toml")
        return False
    except Exception as e:
        st.error(f"An error occurred during Gemini configuration: {e}")
        return False

def clean_json_string(json_string):
    """
    Cleans a string to make it valid JSON, removing markdown backticks
    and attempting to fix common LLM formatting issues.
    """
    # Remove markdown JSON block indicators
    cleaned_string = re.sub(r"```json\s*([\s\S]*?)\s*```", r"\1", json_string)
    cleaned_string = re.sub(r"```([\s\S]*?)```", r"\1", cleaned_string) # General backticks

    # Strip leading/trailing whitespace that might interfere
    cleaned_string = cleaned_string.strip()

    # Sometimes LLMs add trailing commas that break JSON
    cleaned_string = re.sub(r",\s*([\}\]])", r"\1", cleaned_string)

    return cleaned_string

def get_gemini_response(prompt_text: str,
                        model_name: str = DEFAULT_MODEL_NAME,
                        expect_json: bool = True):
    """
    Sends a prompt to the Gemini API and returns the response.

    Args:
        prompt_text (str): The prompt to send to the LLM.
        model_name (str): The Gemini model to use.
        expect_json (bool): If True, sets response_mime_type to application/json
                            and attempts to parse the response as JSON.

    Returns:
        str or dict or list: The processed response from Gemini (parsed JSON if expect_json is True and successful),
                             or None if an error occurs.
    """
    if not configure_gemini():
        return None

    try:
        model = genai.GenerativeModel(
            model_name,
            safety_settings=DEFAULT_SAFETY_SETTINGS,
            generation_config=DEFAULT_GENERATION_CONFIG if expect_json else None # Only set mime type if expecting JSON
        )

        # Log the prompt being sent (optional, for debugging)
        # st.write("--- DEBUG: Sending Prompt to Gemini ---")
        # st.text(prompt_text)
        # st.write("--- END DEBUG ---")

        response = model.generate_content(prompt_text)

        if response.candidates:
            generated_text = response.text
            # st.write("--- DEBUG: Raw LLM Output ---") # For debugging
            # st.text(generated_text)
            # st.write("--- END DEBUG ---")

            if expect_json:
                cleaned_text = clean_json_string(generated_text)
                try:
                    return json.loads(cleaned_text)
                except json.JSONDecodeError as e:
                    st.error(f"LLM did not return valid JSON after cleaning. Error: {e}")
                    st.caption("Cleaned LLM output that failed to parse:")
                    st.code(cleaned_text, language="text")
                    return None
            else:
                return generated_text # Return raw text if not expecting JSON
        else:
            st.warning("Gemini API returned no candidates in the response.")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                st.warning(f"Prompt Feedback: {response.prompt_feedback}")
            return None

    except Exception as e:
        st.error(f"Error communicating with Gemini API: {e}")
        # Consider more detailed logging for production if needed
        # print(f"Full Gemini API error details: {e}")
        return None

if __name__ == "__main__":
    # This block is for testing llm_handler.py directly.
    # You would need to set up secrets.toml for this to run.
    st.set_page_config(layout="wide")
    st.title("LLM Handler Test Interface")

    st.info("Ensure your .streamlit/secrets.toml file has GEMINI_API_KEY set.")

    test_prompt_text = st.text_area("Enter test prompt:",
                                    'Suggest 3 fun activities for a weekend in London. Format as a JSON list of strings, where each string is an activity. Example: ["Visit Buckingham Palace", "Ride the London Eye", "Explore the British Museum"]',
                                    height=150)
    expect_json_output = st.checkbox("Expect JSON output from LLM?", value=True)

    if st.button("Send Test Prompt to Gemini"):
        if not test_prompt_text:
            st.warning("Please enter a prompt.")
        else:
            with st.spinner("Calling Gemini API..."):
                result = get_gemini_response(test_prompt_text, expect_json=expect_json_output)

            st.subheader("Response from Gemini:")
            if result is not None:
                if expect_json_output:
                    st.json(result)
                else:
                    st.markdown(result)
            else:
                st.error("Failed to get a response or an error occurred.")