import io
import mimetypes
import os
import json
import time
import jwt
import platform
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
import openai
from azure.identity.aio import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from azure.search.documents.aio import SearchClient
from azure.storage.blob.aio import BlobServiceClient
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from quart import (
    Blueprint,
    Quart,
    abort,
    current_app,
    jsonify,
    request,
    send_file,
)

from quart_cors import cors
from quart_schema import QuartSchema, Info, document_request, document_response

from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from core.modelhelper import cgsIndexColumnFacetDist, applicationLog


CONFIG_OPENAI_TOKEN = "openai_token"
CONFIG_CREDENTIAL = "azure_credential"
CONFIG_ASK_APPROACHES = "ask_approaches"
CONFIG_CHAT_APPROACHES = "chat_approaches"
CONFIG_BLOB_CONTAINER_CLIENT = "blob_container_client"
CONFIG_SEARCH_CLIENT = "search_client"

# initialize Allowed Role
ALLOWED_ROLE = os.getenv("AZURE_AUTH_ROLE")

if ALLOWED_ROLE is None:
    ALLOWED_ROLE = "all"


# the authentication and validity of token is handled by Azure
# therefore, this method to check the role is valid
# no check with the respective AD is required in this way
# before request is not possible, as there the header is not readable
async def checkAuthorization(request):
    if ALLOWED_ROLE != "all":
        auth_header = request.headers.get("Authorization")
        parts = auth_header.split()
        token = parts[1]
        try:
            decoded_token = jwt.decode(
                jwt=token, algorithms=["RS256"], options={"verify_signature": False}
            )
        except jwt.exceptions.InvalidTokenError:
            return 401
        if ALLOWED_ROLE not in decoded_token["roles"]:
            return 403


bp = Blueprint("routes", __name__)

if platform.system() == "Darwin":
    print("cors disabled")
    bp = cors(bp, allow_origin="*")


@dataclass
class History:
    user: str
    bot: Optional[str]


@dataclass
class Overrides:
    retrieval_mode: str
    semantic_ranker: bool
    semantic_captions: bool
    top: int
    temperature: float


@dataclass
class ChatRequestData:
    history: List[History]
    approach: str = "rrr"
    overrides: Overrides = None


@dataclass
class DataPoint:
    """Endpoint for adding feedback to Application Insights for later evaluation"""

    docName: str
    page: int


@dataclass
class ChatResponseData:
    answer: str
    keywords: str
    data_points: List[DataPoint]


@dataclass
class ErrorChatResponseData:
    answer: str
    keywords: str


@dataclass
class CatResponse:
    categories: List[str]


@dataclass
class ErrorResponse:
    error: str


@dataclass
class FeedbackRequestData:
    history: List[History]
    opinion: int


@dataclass
class FeedbackResponseData:
    response: str


@bp.route("/category", methods=["GET"])
@document_response(CatResponse, 200)
@document_response(ErrorResponse, 400)
async def category():
    authorization = await checkAuthorization(request)
    if authorization == 403 or authorization == 401:
        return (
            jsonify(
                {"error": {"code": 403, "message": f"role {ALLOWED_ROLE} is missing"}}
            ),
            403,
        )
    """Endpoint for receiving the available categories"""
    try:
        search_client = current_app.config[CONFIG_SEARCH_CLIENT]
        search_res = await cgsIndexColumnFacetDist(search_client, "category")
        values = [item["value"] for item in search_res]
        res = {"categories": values}
        return jsonify(res)
    except Exception as e:
        res = {"error": e.args[0]}
        return (jsonify({"error": {"code": 500, "message": str(e)}}), 500)


@bp.route("/chat", methods=["POST"])
@document_request(ChatRequestData)
@document_response(ChatResponseData, 200)
@document_response(ErrorChatResponseData, 400)
@document_response(ErrorChatResponseData, 429)
@document_response(ErrorChatResponseData, 500)
async def chat():
    """Endpoint for chatting with the custom model"""
    authorization = await checkAuthorization(request)
    if authorization == 403 or authorization == 401:
        return (
            jsonify(
                {"error": {"code": 403, "message": f"role {ALLOWED_ROLE} is missing"}}
            ),
            403,
        )
    if not request.is_json:
        return (
            jsonify({"error": {"code": 415, "message": "request must be json"}}),
            415,
        )
    request_json = await request.get_json()
    approach = request_json["approach"]
    try:
        impl = current_app.config[CONFIG_CHAT_APPROACHES].get(approach)
        if not impl:
            return (
                jsonify({"error": {"code": 400, "message": "unknown approach"}}),
                400,
            )
        # Workaround for: https://github.com/openai/openai-python/issues/371
        async with aiohttp.ClientSession() as s:
            openai.aiosession.set(s)
            r = await impl.run(
                request_json["history"], request_json.get("overrides") or {}
            )
        if r["keywords"] == "error":
            return (jsonify({"error": {"code": 500, "message": r["answer"]}}), 500)
        elif r["keywords"] == "ratelimit":
            return (
                jsonify(
                    {
                        "error": {
                            "code": 429,
                            "message": "current ratelimit reached",
                        }
                    }
                ),
                429,
            )
        # return answer if no error
        return jsonify(r)
    except Exception as e:
        applicationLog("Exception in /chat", "exc")
        return (jsonify({"error": {"code": 500, "message": str(e)}}), 500)


# Serve content files from blob storage from within the app to keep the example self-contained.
# *** NOTE *** this assumes that the content files are public, or at least that all users of the app
# can access all the files. This is also slow and memory hungry.
@bp.route("/content/<path>", methods=["GET"])
async def content(path):
    authorization = await checkAuthorization(request)
    if authorization == 403 or authorization == 401:
        return (
            jsonify(
                {"error": {"code": 403, "message": f"role {ALLOWED_ROLE} is missing"}}
            ),
            403,
        )
    """Endpoint for downloading pdfs from storage blob"""
    blob_container_client = current_app.config[CONFIG_BLOB_CONTAINER_CLIENT]
    blob = await blob_container_client.get_blob_client(path).download_blob()
    if not blob.properties or not blob.properties.has_key("content_settings"):
        abort(404)
    mime_type = blob.properties["content_settings"]["content_type"]
    if mime_type == "application/octet-stream":
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    blob_file = io.BytesIO()
    await blob.readinto(blob_file)
    blob_file.seek(0)
    return await send_file(
        blob_file, mimetype=mime_type, as_attachment=False, attachment_filename=path
    )


@bp.route("/feedback", methods=["POST"])
@document_request(FeedbackRequestData)
@document_response(FeedbackResponseData)
@document_response(ErrorChatResponseData, 400)
async def feedback():
    authorization = await checkAuthorization(request)
    if authorization == 403 or authorization == 401:
        return (
            jsonify(
                {"error": {"code": 403, "message": f"role {ALLOWED_ROLE} is missing"}}
            ),
            403,
        )
    """Endpoint for adding feedback to Application Insights for later evaluation"""
    try:
        request_json = await request.get_json()
        if len(request_json["history"]) > 0:
            applicationLog(json.dumps(request_json))
        return jsonify({"message": "feedback has been forwarded"})
    except Exception as e:
        return (jsonify({"error": {"code": 500, "message": str(e)}}), 500)


@bp.before_request
async def ensure_openai_token():
    openai_token = current_app.config[CONFIG_OPENAI_TOKEN]
    if openai_token.expires_on < time.time() + 60:
        openai_token = await current_app.config[CONFIG_CREDENTIAL].get_token(
            "https://cognitiveservices.azure.com/.default"
        )
        current_app.config[CONFIG_OPENAI_TOKEN] = openai_token
        openai.api_key = openai_token.token


@bp.before_app_serving
async def setup_clients():
    AZURE_STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")
    AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER_DOCS")
    AZURE_SEARCH_SERVICE = os.getenv("AZURE_SEARCH_SERVICE")
    AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
    AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE")
    AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
    AZURE_OPENAI_CHATGPT_MODEL = os.getenv("AZURE_OPENAI_CHATGPT_MODEL")
    AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
    MAX_TOKENS_QUERY = os.getenv("MAX_TOKENS_QUERY") or 32
    MAX_TOKENS_ANSWER = os.getenv("MAX_TOKENS_ANSWER") or 1024

    KB_FIELDS_CONTENT = os.getenv("KB_FIELDS_CONTENT", "content")
    KB_FIELDS_SOURCEPAGE = os.getenv("KB_FIELDS_SOURCEPAGE", "sourcepage")

    # Use the current user identity to authenticate with Azure OpenAI, Cognitive Search and Blob Storage
    # just use 'az login' locally, and managed identity when deployed on Azure). If you need to use keys,
    # use separate AzureKeyCredential instances with the keys for each service
    # If you encounter a blocking error during a DefaultAzureCredential resolution,
    # you can exclude the problematic credential by using a parameter (ex. exclude_shared_token_cache_credential=True)

    azure_credential = DefaultAzureCredential(
        exclude_shared_token_cache_credential=True
    )

    # Set up clients for Cognitive Search and Storage
    search_client = SearchClient(
        endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
        index_name=AZURE_SEARCH_INDEX,
        credential=azure_credential,
    )
    blob_client = BlobServiceClient(
        account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
        credential=azure_credential,
    )
    blob_container_client = blob_client.get_container_client(AZURE_STORAGE_CONTAINER)

    # Find out which document languages are present and which is the most common to set it later as
    # a default language in the environment
    facets_results = await cgsIndexColumnFacetDist(search_client, "doclang")
    os.environ["FACETS_RESULTS"] = str(facets_results)
    print(facets_results)

    # Used by the OpenAI SDK
    openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
    openai.api_version = "2023-05-15"
    openai.api_type = "azure_ad"
    openai_token = await azure_credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    )
    openai.api_key = openai_token.token

    # Store on app.config for later use inside requests
    current_app.config[CONFIG_OPENAI_TOKEN] = openai_token
    current_app.config[CONFIG_CREDENTIAL] = azure_credential
    current_app.config[CONFIG_BLOB_CONTAINER_CLIENT] = blob_container_client
    current_app.config[CONFIG_SEARCH_CLIENT] = search_client

    # Various approaches to integrate GPT and external knowledge,
    # most applications will use a single one of these patterns or some derivative,
    # here we include several for exploration purposes
    current_app.config[CONFIG_ASK_APPROACHES] = {
        "rrr": ChatReadRetrieveReadApproach(
            search_client,
            AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            AZURE_OPENAI_CHATGPT_MODEL,
            AZURE_OPENAI_EMB_DEPLOYMENT,
            KB_FIELDS_SOURCEPAGE,
            KB_FIELDS_CONTENT,
            MAX_TOKENS_QUERY,
            MAX_TOKENS_ANSWER,
        )
    }
    current_app.config[CONFIG_CHAT_APPROACHES] = {
        "rrr": ChatReadRetrieveReadApproach(
            search_client,
            AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            AZURE_OPENAI_CHATGPT_MODEL,
            AZURE_OPENAI_EMB_DEPLOYMENT,
            KB_FIELDS_SOURCEPAGE,
            KB_FIELDS_CONTENT,
            MAX_TOKENS_QUERY,
            MAX_TOKENS_ANSWER,
        )
    }


def create_app():
    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        configure_azure_monitor()
        AioHttpClientInstrumentor().instrument()
        LoggingInstrumentor().instrument()
    app = Quart(__name__)
    app.register_blueprint(bp)
    app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)
    QuartSchema(app, info=Info(title="Telekom LLM & CompanyData API", version="1.0"))

    return app
