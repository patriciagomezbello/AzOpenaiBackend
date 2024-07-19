# Mate Backend

## Setup

See [docs](../../docs/dev/README.md).

## Development

1. Execute `make mate` in the root directory to run the backend. 
2. Once it is running you can test it locally by visting [`http://localhost:50505/docs`](http://localhost:50505/docs). 
3. Authorize your requests: 
    - by copying a JWT Token from a live application or the local Frontend
    - or use this script if you have a working machine account/service principal: 
    
        ```python
        import requests
        
        # tenant_id
        tenant_id = "xxxx"
        
        # client_id of the app registration that has access to the API
        client_id = "xxxx"
        
        # client_secret, choose if loaded from env or directly supply it here
        client_secret = os.getenv("client_secret")
        client_secret = "xxxx"
        
        
        login_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        
        # scope -> client_id of the API that you want to access + "/.default"
        scope = "api_client_id/.default"
        
        # Get access token
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope,
        }
        response_token = requests.post(login_url, data=payload)
        
        access_token = response_token.json().get("access_token")
        
        print(access_token)
        ```
        
        Run `pip install python-dotenv requests` for installing the dependecies.

