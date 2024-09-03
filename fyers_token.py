from dotenv import load_dotenv
from fyers_apiv3 import fyersModel
import webbrowser
import os
import requests
import hashlib
import json

# Load environment variables from .env file
load_dotenv()

# Input parameters
redirect_uri = os.getenv('REDIRECT_URI')
client_id = os.getenv('CLIENT_ID')
secret_key = os.getenv('SECRET_KEY')

# Get the current working directory
current_directory = os.getcwd()
log_path = current_directory

# Function to generate access token using refresh token
def generate_token_from_refresh(client_id, secret_key, refresh_token):
    url = 'https://api-t1.fyers.in/api/v3/validate-refresh-token'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'grant_type': 'refresh_token',
        'appIdHash': hashlib.sha256(f"{client_id}:{secret_key}".encode()).hexdigest(),
        'refresh_token': refresh_token,
        'pin': '2612'  # You might want to store this in .env file as well
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

# Try to load existing refresh token
refresh_token_path = os.path.join(current_directory, "refresh_token.txt")
if os.path.exists(refresh_token_path):
    with open(refresh_token_path, 'r') as file:
        refresh_token = file.read().strip()
    
    # Try to generate access token using refresh token
    access_token = generate_token_from_refresh(client_id, secret_key, refresh_token)
    
    if access_token:
        print("Access token generated using refresh token")
    else:
        print("Failed to generate access token using refresh token. Falling back to auth code method.")
else:
    print("Refresh token not found. Using auth code method.")
    access_token = None

# If access token is not generated, use the auth code method
if not access_token:
    grant_type = "authorization_code"
    response_type = "code"
    state = "sample"
    
    appSession = fyersModel.SessionModel(
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type=response_type,
        state=state,
        secret_key=secret_key,
        grant_type=grant_type
    )

    generateTokenUrl = appSession.generate_authcode()
    print(f"Login URL: {generateTokenUrl}")
    webbrowser.open(generateTokenUrl, new=1)

    auth_code = input("Enter Auth Code: ")
    appSession.set_token(auth_code)
    response = appSession.generate_token()

    try:
        access_token = response["access_token"]
        refresh_token = response["refresh_token"]
        print("Token generated using auth code")
        
        # Save refresh token for future use
        with open(refresh_token_path, 'w') as file:
            file.write(refresh_token)
    except KeyError as e:
        print(f"Error retrieving tokens: {e}")
        print("Response:", response)
        exit(1)

# Initialize the FyersModel with the access token
fyers = fyersModel.FyersModel(token=access_token, is_async=False, client_id=client_id, log_path=log_path)

# Get details about your account
response = fyers.get_profile()
print(response)

# Save client_id and access_token to text files
with open(os.path.join(current_directory, "client_id.txt"), 'w') as file:
    file.write(client_id)

with open(os.path.join(current_directory, "access_token.txt"), 'w') as file:
    file.write(access_token)