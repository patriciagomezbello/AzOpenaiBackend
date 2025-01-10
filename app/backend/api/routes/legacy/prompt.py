from typing import Any

from api.errors import ErrorProvider
from api.models import ErrorResponse
from api.routes.legacy.models import PromptCreationResponse
from api.routes.legacy.models import PromptRequest
from api.routes.legacy.models import PromptResponse
from containers import DIContainer
from dependency_injector.wiring import inject
from dependency_injector.wiring import Provide
from quart import Blueprint
from quart import jsonify
from quart import request
from quart import ResponseReturnValue
from quart_schema import document_request
from quart_schema import document_response
from quart_schema import tag
from services.auth import secure_endpoint
from services.logger import new_logger
from services.prompts import AzurePromptService
from services.schemas import NewPrompt


logger = new_logger(__name__)
bp = Blueprint("prompt", __name__)


@bp.route("/prompts", methods=["GET"])
@tag(["/v1"])
@document_response(PromptResponse, 200)
@document_response(ErrorResponse, 401)
@document_response(ErrorResponse, 403)
@document_response(ErrorResponse, 500)
@secure_endpoint
@inject
async def prompt(
    prompt_service: AzurePromptService = Provide[DIContainer.azure_table_service],
) -> ResponseReturnValue:
    """Endpoint for receiving all available prompts from the storage account tablke.

    This endpoint is used to retrieve all prompts from the table in the storage account.
    It is a protected endpoint and requires a valid JWT token to access it.
    """
    try:
        prompts = await prompt_service.get_prompts()
        prompts_dict = [prompt.__to_dict__() for prompt in prompts]
        return (jsonify({"prompts": prompts_dict}), 200)
    except Exception as e:
        logger.error("Error while getting prompts", {"error": str(e)})
        return ErrorProvider.error_response("Error while getting prompts", 500, error=e)


@bp.route("/prompts", methods=["POST"])
@tag(["/v1"])
@document_request(PromptRequest)
@document_response(PromptCreationResponse, 200)
@document_response(ErrorResponse, 401)
@document_response(ErrorResponse, 403)
@document_response(ErrorResponse, 500)
@secure_endpoint
@inject
async def create_prompt(
    prompt_service: AzurePromptService = Provide[DIContainer.azure_table_service],
) -> ResponseReturnValue:
    """Endpoint for creating a new prompt via the frontend.

    This endpoint is used to create a new prompt and save it to the storage account table.
    It is a protected endpoint and requires a valid JWT token to access it.
    """
    if not request.is_json:
        return ErrorProvider.error_response_with_message(ErrorProvider.INVALID_JSON)
    try:
        data: dict[str, Any] = await request.get_json()

        try:
            new_prompt = NewPrompt(
                name=data["PromptName"],
                prompt=data["Prompt"],
            )
            if not new_prompt.is_valid():
                return ErrorProvider.error_response_with_message(ErrorProvider.MALFORMED_REQUEST)
        except KeyError:
            return ErrorProvider.error_response_with_message(ErrorProvider.MALFORMED_REQUEST)

        await prompt_service.create_prompt(prompt=new_prompt)
        return jsonify({"response": f"Prompt {new_prompt.name} was successfully created."}), 200

    except Exception as e:
        logger.exception("Error while creating new prompt", {"error": str(e)})
        return ErrorProvider.error_response("Error while creating new prompt", 500, error=e)
