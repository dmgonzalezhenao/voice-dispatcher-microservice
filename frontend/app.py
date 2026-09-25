"""
Voice AI Dispatcher - Streamlit Interactive Frontend
=====================================================

This module implements the user interface for the Voice AI Dispatcher microservice.

It connects to the FastAPI backend, allowing users to configure synthesis settings,
submit multiple text phrases for parallel execution, monitor real-time processing 
latency, and play or download the resulting audio files hosted on Supabase Storage.
"""

import os
import httpx
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file for local development configuration
load_dotenv()

# Define backend default service URL and authorization secret key
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "")
DEFAULT_API_KEY = os.getenv("API_SECRET_KEY", "")


# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Voice AI Dispatcher",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎙️ Voice AI Dispatcher Dashboard")
st.caption("High-performance asynchronous microservice for parallel text-to-speech synthesis and cloud persistence.")


# --- Sidebar: Microservice Credentials & Settings ---
with st.sidebar:
    st.header("⚙️ System Configuration")
    
    # Optional ElevenLabs dynamic key override
    elevenlabs_key_override = st.text_input(
        "Custom ElevenLabs API Key (Optional)",
        value="",
        type="password",
        help="Optional dynamic key override. Leave empty to use system environment default."
    )

    st.info("💡 **Note:** You have **3 free uses per day**. For unlimited use, enter your own ElevenLabs key above.")
    
    st.divider()
    
    st.header("🎛️ Voice Settings")
    
    # Preset native free voice selection
    voice_options = {
        "Adam (Multilingual Male - Free)": "pNInz6obpgDQGcFmaJgB",
        "George (Warm & Deep Male - Free)": "JBFqnCBsd6RMkjVDRZzb",
        "Custom Voice ID": "custom"
    }
    
    selected_voice_label = st.selectbox("Select Voice Profile", list(voice_options.keys()))
    
    if voice_options[selected_voice_label] == "custom":
        target_voice_id = st.text_input("Enter Custom Voice ID", value="")
    else:
        target_voice_id = voice_options[selected_voice_label]

    # Fine-tuning sliders
    stability_val = st.slider(
        "Stability",
        min_value=0.0,
        max_value=1.0,
        value=0.50,
        step=0.05,
        help="Higher values increase vocal consistency; lower values increase emotion."
    )
    
    similarity_val = st.slider(
        "Similarity Boost",
        min_value=0.0,
        max_value=1.0,
        value=0.75,
        step=0.05,
        help="Controls adherence to original speaker clarity and tone."
    )


# --- Main Layout: Text Input Area ---
st.subheader("📝 Batch Phrase Input")
st.markdown("Enter up to **5 text phrases** (one per line) to process simultaneously using parallel `asyncio` execution.")

default_phrases = (
    "Hola, esta es la primera frase sintetizada en paralelo.\n"
    "El procesamiento asíncrono reduce la latencia de respuesta significativamente.\n"
    "Los archivos de audio resultantes se almacenan de forma segura en Supabase Storage."
)

input_text = st.text_area(
    "Phrases to synthesize",
    value=default_phrases,
    height=150,
    placeholder="Enter each phrase on a new line..."
)

# Parse raw line-separated text into a clean list of phrases
parsed_phrases = [line.strip() for line in input_text.split("\n") if line.strip()]


# --- Execution Trigger Button ---
if st.button("⚡ Dispatch Parallel Voice Synthesis", type="primary", use_container_width=True):
    
    # Input validation checks
    if not parsed_phrases:
        st.error("Please enter at least one phrase to synthesize.")
    elif len(parsed_phrases) > 5:
        st.warning("Maximum batch size exceeded! Please limit your request to a maximum of 5 phrases.")
    else:
        # Construct backend API request payload
        payload = {
            "phrases": parsed_phrases,
            "voice_id": target_voice_id if target_voice_id else None,
            "delivery_mode": "cloud_url",
            "settings": {
                "stability": stability_val,
                "similarity_boost": similarity_val
            }
        }
        
        # Prepare custom HTTP headers for backend request
        headers = {
            "X-API-KEY": DEFAULT_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Add dynamic ElevenLabs key header if provided
        if elevenlabs_key_override.strip():
            headers["X-ElevenLabs-Key"] = elevenlabs_key_override.strip()

        dispatch_endpoint = f"{DEFAULT_BACKEND_URL.rstrip('/')}/api/v1/dispatch"

        # Execute HTTP POST request with loading spinner
        with st.spinner("Synthesizing audio phrases and uploading to Supabase CDN in parallel..."):
            try:
                # Issue synchronous HTTP call to FastAPI microservice using httpx
                response = httpx.post(dispatch_endpoint, json=payload, headers=headers, timeout=60.0)
                
                # Check for successful 200 OK response
                if response.status_code == 200:
                    data = response.json()
                    
                    st.success("Batch dispatch completed successfully!")
                    
                    # Display performance latency metrics
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Status", data.get("status", "success").upper())
                    col2.metric("Total Items Processed", data.get("total_processed", 0))
                    col3.metric("Execution Latency", f"{data.get('elapsed_time_seconds', 0.0)} s")
                    
                    st.divider()
                    st.subheader("🔊 Generated Audio Assets")
                    
                    # Iterate over results and render audio players with download buttons
                    for idx, result_item in enumerate(data.get("results", []), start=1):
                        with st.container():
                            st.markdown(f"**Phrase {idx}:** *\"{result_item['phrase']}\"*")
                            
                            # Render embedded HTML5 audio player using Supabase public CDN URL
                            st.audio(result_item["audio_data"], format="audio/mp3")
                            
                            # Display raw public CDN URL link
                            st.caption(f"☁️ Public CDN Link: [{result_item['audio_data']}]({result_item['audio_data']})")
                            st.divider()
                else:
                    # Handle backend API error status codes
                    st.error(f"Backend HTTP Error ({response.status_code}):")
                    st.code(response.text, language="json")

            except httpx.RequestError as exc:
                # Handle networking connection failures
                st.error(f"Could not connect to FastAPI microservice at `{dispatch_endpoint}`.")
                st.info(f"Details: {str(exc)}")