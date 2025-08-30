# main.py
# Import necessary libraries
import os
from datetime import datetime
import pytz
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import APIKeyHeader

# --- Configuration ---
# In a real-world application, it's best practice to load secrets from environment variables.
# You can set this variable in your terminal before running the app.
# If not set, it will use the default value provided.
SECRET_TOKEN = os.getenv("API_SECRET_TOKEN", "your-secret-token-here")

# Define the security scheme for the API key header.
# We expect a header in the format: 'Authorization: your-secret-token-here'
api_key_header_auth = APIKeyHeader(name="Authorization", auto_error=False)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Time Service API",
    description="An API to get the current time",
    version="1.0.0",
)


# --- Dependency for Authorization ---
async def verify_token(api_key_header: str = Depends(api_key_header_auth)):
    """
    This is a dependency function that verifies the 'Authorization' header.
    It's automatically called for any endpoint that includes it.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing or invalid.
    """
    if api_key_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
            headers={"WWW-Authenticate": "Token"},
        )
    if api_key_header != SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Token",
            headers={"WWW-Authenticate": "Token"},
        )
    return api_key_header


# --- API Endpoint ---
@app.get("/", dependencies=[Depends(verify_token)])
async def get_current_time():
    """
    This is the root endpoint. It returns the current time in Latvia.
    Access is protected and requires a valid token in the 'Authorization' header.
    """
    # Set the timezone to Latvia (Europe/Riga)
    latvia_timezone = pytz.timezone("Europe/Riga")

    # Get the current time in the specified timezone
    time_in_latvia = datetime.now(latvia_timezone)

    # Format the time nicely for the JSON response
    formatted_time = time_in_latvia.strftime("%Y-%m-%d %H:%M:%S %Z")

    return {"location": "Latvia", "current_time": formatted_time}

# To run this app:
# 1. Save the file as main.py
# 2. Install the requirements: pip install -r requirements.txt
# 3. In your terminal, run: uvicorn main:app --reload
# 4. To set a custom secret token, use an environment variable:
#    export API_SECRET_TOKEN="my-super-secret-key"
#    uvicorn main:app --reload
