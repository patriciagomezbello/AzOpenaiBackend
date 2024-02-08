import io
import mimetypes
import os
import json
import platform
from openai import AsyncAzureOpenAI
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from azure.monitor.opentelemetry import configure_azure_monitor
from azure.search.documents.aio import SearchClient
from azure.storage.blob.aio import BlobServiceClient
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from quart import (
    Blueprint,
    Quart,
    current_app,
    jsonify,
    request,
    send_file,
)

from quart_cors import cors
from quart_schema import QuartSchema, Info, document_request, document_response

from approaches.chatreadretrieveread import ChatReadRetrieveReadApproach
from core.auth import Auth
from core.dataclasses import (
    ChatRequestData,
    ChatResponseData,
    CatResponse,
    FeedbackRequestData,
    ErrorResponseData,
    FeedbackResponseData,
)
from core.error import (
    error_message_auth,
    error_message_unknown_approach,
    error_message_json,
    error_message_ratelimit,
    error_message_doc_not_found,
    error_response,
)
from core.modelhelper import cgsIndexColumnFacetDist, applicationLog

CONFIG_OPENAI_CLIENT = "openai_client"
CONFIG_CREDENTIAL = "azure_credential"
CONFIG_CHAT_APPROACHES = "chat_approaches"
CONFIG_BLOB_CONTAINER_CLIENT = "blob_container_client"
CONFIG_SEARCH_CLIENT = "search_client"

auth = Auth()

bp = Blueprint("routes", __name__)

# for local mac development
if platform.system() == "Darwin":
    print("cors disabled")
    bp = cors(bp, allow_origin="*")


@bp.route("/categories", methods=["GET"])
@document_response(CatResponse, 200)
@document_response(ErrorResponseData, 400)
@document_response(ErrorResponseData, 403)
async def categories():
    """Endpoint for receiving the available categories"""
    if not auth.is_authorized(request):
        return error_response(message=error_message_auth, code=403)
    try:
        search_client = current_app.config[CONFIG_SEARCH_CLIENT]
        search_res = await cgsIndexColumnFacetDist(search_client, "category")
        values = [item["value"] for item in search_res]
        res = {"categories": values}
        return jsonify(res)
    except Exception as e:
        return error_response(str(e), 500)


@bp.route("/chat", methods=["POST"])
@document_request(ChatRequestData)
@document_response(ChatResponseData, 200)
@document_response(ErrorResponseData, 400)
@document_response(ErrorResponseData, 403)
@document_response(ErrorResponseData, 415)
@document_response(ErrorResponseData, 429)
@document_response(ErrorResponseData, 500)
async def chat():
    """Endpoint for chatting with the custom model"""
    if not auth.is_authorized(request):
        return error_response(message=error_message_auth, code=403)
    if not request.is_json:
        return error_response(message=error_message_json, code=415)
    try:
        request_json = await request.get_json()
        approach = request_json["approach"]
        impl = current_app.config[CONFIG_CHAT_APPROACHES].get(approach)
        if not impl:
            return error_response(message=error_message_unknown_approach, code=400)
        r = await impl.run(request_json["history"], request_json.get("overrides") or {})
        if r.get("error"):
            if r.get("code") == 429:
                return error_response(message=error_message_ratelimit, code=429)
            else:
                return error_response(r.get("error"), 500)
        # return answer if no error
        return jsonify(r)
    except Exception as e:
        applicationLog("Exception in /chat", "exc")
        return error_response(str(e), 500)


# Serve content files from blob storage from within the app to keep the example self-contained.
# *** NOTE *** this assumes that the content files are public, or at least that all users of the app
# can access all the files. This is also slow and memory hungry.
@bp.route("/content/<path>", methods=["GET"])
@document_response(ErrorResponseData, 403)
@document_response(ErrorResponseData, 404)
async def content(path):
    """Endpoint for downloading pdfs from storage blob"""
    if not auth.is_authorized(request):
        return error_response(message=error_message_auth, code=403)
    blob_container_client = current_app.config[CONFIG_BLOB_CONTAINER_CLIENT]
    try:
        blob = await blob_container_client.get_blob_client(path).download_blob()
    except Exception:
        return error_response(message=error_message_doc_not_found, code=404)
    if not blob.properties or not blob.properties.has_key("content_settings"):
        return error_response(message=error_message_doc_not_found, code=404)
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
@document_response(ErrorResponseData, 400)
@document_response(ErrorResponseData, 403)
async def feedback():
    """Endpoint for adding feedback to Application Insights for later evaluation"""
    if not auth.is_authorized(request):
        return error_response(message=error_message_auth, code=403)
    try:
        request_json = await request.get_json()
        if len(request_json["history"]) > 0:
            applicationLog(json.dumps(request_json))
        return jsonify({"message": "feedback has been forwarded"})
    except Exception as e:
        return error_response(str(e), 500)


@bp.before_app_serving
async def setup_clients():
    # Storage settings
    AZURE_STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")
    AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER_DOCS")
    # AI Search settings
    AZURE_SEARCH_SERVICE = os.getenv("AZURE_SEARCH_SERVICE")
    AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
    # OpenAI settings
    AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE")
    AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT")
    AZURE_OPENAI_CHATGPT_MODEL = os.getenv("AZURE_OPENAI_CHATGPT_MODEL")
    AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")

    if (
        AZURE_OPENAI_SERVICE is None
        or AZURE_OPENAI_CHATGPT_DEPLOYMENT is None
        or AZURE_OPENAI_CHATGPT_MODEL is None
        or AZURE_OPENAI_EMB_DEPLOYMENT is None
    ):
        raise ValueError(
            "AZURE_OPENAI_ + SERVICE, CHATGPT_DEPLOYMENT, CHATGPT_MODEL or EMB_DEPLOYMENT is not set"
        )
    # Chat settings
    MAX_TOKENS_QUERY = int(os.getenv("MAX_TOKENS_QUERY", 32))
    MAX_TOKENS_ANSWER = int(os.getenv("MAX_TOKENS_ANSWER", 1024))
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
    if AZURE_SEARCH_INDEX is not None:
        search_client = SearchClient(
            endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
            index_name=AZURE_SEARCH_INDEX,
            credential=azure_credential,  # type: ignore
        )
    else:
        raise ValueError("AZURE_SEARCH_INDEX is not set")
    blob_client = BlobServiceClient(
        account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
        credential=azure_credential,  # type: ignore
    )
    if AZURE_STORAGE_CONTAINER is not None:
        blob_container_client = blob_client.get_container_client(
            AZURE_STORAGE_CONTAINER
        )
    else:
        raise ValueError("AZURE_STORAGE_CONTAINER_DOCS is not set")

    # Find out which document languages are present and which is the most common to set it later as
    # a default language in the environment
    facets_results = await cgsIndexColumnFacetDist(search_client, "doclang")
    os.environ["FACETS_RESULTS"] = str(facets_results)
    applicationLog(facets_results, "info")

    # OpenAI setup
    token_provider = get_bearer_token_provider(
        azure_credential, "https://cognitiveservices.azure.com/.default"
    )

    openai_client = AsyncAzureOpenAI(
        api_version="2023-07-01-preview",
        azure_endpoint=f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com",
        azure_ad_token_provider=token_provider,
    )

    # Store on app.config for later use inside requests
    current_app.config[CONFIG_OPENAI_CLIENT] = openai_client
    current_app.config[CONFIG_CREDENTIAL] = azure_credential
    current_app.config[CONFIG_BLOB_CONTAINER_CLIENT] = blob_container_client
    current_app.config[CONFIG_SEARCH_CLIENT] = search_client

    # Various approaches to integrate GPT and external knowledge,
    # most applications will use a single one of these patterns or some derivative,
    # here we include several for exploration purposes
    current_app.config[CONFIG_CHAT_APPROACHES] = {
        "rrr": ChatReadRetrieveReadApproach(
            search_client,
            openai_client,
            AZURE_OPENAI_CHATGPT_DEPLOYMENT,
            AZURE_OPENAI_CHATGPT_MODEL,
            AZURE_OPENAI_EMB_DEPLOYMENT,
            KB_FIELDS_SOURCEPAGE,
            KB_FIELDS_CONTENT,
            MAX_TOKENS_QUERY,
            MAX_TOKENS_ANSWER,
        )
    }


@bp.after_app_serving
async def close_clients():
    await current_app.config[CONFIG_SEARCH_CLIENT].close()
    await current_app.config[CONFIG_BLOB_CONTAINER_CLIENT].close()


def create_app():
    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        configure_azure_monitor()
        AioHttpClientInstrumentor().instrument()
        LoggingInstrumentor().instrument()
    app = Quart(__name__)
    app.register_blueprint(bp)
    app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)
    QuartSchema(app, info=Info(title="Telekom LLM & CompanyData API", version="v1.0.0"))

    return app
