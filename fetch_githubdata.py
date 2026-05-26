import os
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get token
TOKEN = os.getenv("GITHUB_TOKEN")

# GitHub API endpoint
url = "https://api.github.com/users/octocat"

# Headers (this is where authentication goes)
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
}

# Make request
response = requests.get(url, headers=headers)
print(response)
# Convert response to JSON
data = response.json()
print(data)
# Print result
print("Username:", data["login"])
print("Followers:", data["followers"])
print("Public repos:", data["public_repos"])