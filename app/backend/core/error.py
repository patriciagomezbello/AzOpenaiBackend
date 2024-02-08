from quart import jsonify
import os

ALLOWED_ROLE = os.getenv("AZURE_AUTH_ROLE", "all")


# The error_response function returns a JSON response with an error message and status code.
error_message_auth = f"role {ALLOWED_ROLE} is missing or invalid token is provided"
error_message_unknown_approach = "unknown approach"
error_message_json = "request must be json"
error_message_ratelimit = "rate limit exceeded"
error_message_doc_not_found = "document not found or not available"


# The error_response function returns a JSON response with an error message and status code.
def error_response(message, code):
    """
    Return a JSON response with an error message and status code
    """
    return (jsonify({"error": {"code": code, "message": message}}), code)
