from typing import List
from typing import Optional

from api.models import ChatMessage
from api.models import ChatResponse
from api.models import Overrides
from api.models import SearchMode
from chats.interfaces import ChatApproach
from chats.interfaces import ChatResponseType
from config import Config
from lingua import Language
from services.citation import CitationService
from services.factory import ServiceFactory
from services.factory import ServiceName
from services.language import LanguageService
from services.llm import LLMService
from services.logger import LOG_SENSITIVE_DATA
from services.logger import new_logger
from services.messages.builder import Builder
from services.schemas import ChatCompletionsOptions
from services.schemas import ChatData
from services.schemas import ContextPrompt
from services.schemas import LLMOptions
from services.schemas import Message
from services.schemas import Model
from services.search import SearchService
from services.timer import timer


logger = new_logger(__name__)


class ChatReadRetrieveRead(ChatApproach):
    """ChatReadRetrieveRead is the chat approach for the read-retrieve-read approach."""

    # NO_IDEA_MESSAGE is the default message if the chat approach has no idea how to respond.
    NO_IDEA_MESSAGES: dict[Language, str] = {
        Language.GERMAN: "Tut mir leid, ich kann Ihnen nicht weiterhelfen. Bitte geben Sie eine spezifischere Frage ein.",
        Language.ENGLISH: "Sorry, I can't help you with that. Please ask a more specific question.",
        Language.HUNGARIAN: "Sajnálom, nem tudok segíteni. Kérlek, tegyél fel egy specifikusabb kérdést.",
        Language.SLOVAK: "Prepáčte, nemôžem vám s tým pomôcť. Prosím, položte konkrétnejšiu otázku.",
        Language.RUSSIAN: "Извините, я не могу вам помочь. Пожалуйста, задайте более конкретный вопрос.",
        Language.SPANISH: "Lo siento, no puedo ayudarte con eso. Por favor, haz una pregunta más específica.",
    }

    # DEFAULT_OVERRIDES are the default overrides for the chat approach.
    DEFAULT_OVERRIDES = Overrides(
        retrieval_mode="",
        semantic_ranker=False,
        semantic_captions=False,
        multilingual_search=True,
        top=3,
        temperature=0.7,
        category_filter=[],
        search_mode=SearchMode.DEFAULT,
    )

    def __init__(self, cfg: Config, svc_factory: ServiceFactory):
        self.config = cfg
        self.search_svcs: dict[SearchMode, SearchService] = {
            SearchMode.DEFAULT: svc_factory.get_service(ServiceName.AZURE_SEARCH_SERVICE),
            SearchMode.EXTENDED: svc_factory.get_service(ServiceName.AZURE_EXTENDED_SEARCH_SERVICE),
            SearchMode.FULL: svc_factory.get_service(ServiceName.AZURE_FULL_SEARCH_SERVICE),
        }
        self.lang_svc: LanguageService = svc_factory.get_service(ServiceName.LANGUAGE_PROCESSING_SERVICE)
        self.llm_svc: LLMService = svc_factory.get_service(ServiceName.OPEN_AI_SERVICE)
        self.citation_service: CitationService = svc_factory.get_service(ServiceName.REGEX_CITATION_SERVICE)

    @timer()
    async def run(
        self,
        history: List[ChatMessage],
        overrides: Optional[Overrides],
        roles: Optional[List[str]],
    ) -> ChatResponseType:
        """run runs the chat approach for the 'read-retrieve-read' approach.
        It uses the cognitive search to enhance the context for the LLM.
        """

        overrides = self._fill_overrides(overrides)
        search_svc = self.search_svcs.get(overrides.search_mode, self.search_svcs[SearchMode.DEFAULT])
        msgs = self._convert_history_to_messages(history, self.llm_svc.config().gpt.model.token_limit())

        try:
            # Get the chat (meta) data from the messages (e.g. which language is used)
            data = await self._get_chat_data(msgs)
            msgs[-1].set_content(self.lang_svc.replace_abbreviations(msgs[-1].content()))

            # Build the (optimized) search query for the cognitive search
            search_query = await search_svc.build_query_prompt(msgs, data)
            logger.debug(
                "Built search query & used temperature", {"search_query": search_query, "temperature": overrides.temperature}
            )

            # Perform the cognitive search to get the enhanced context for the LLM (RAG data)
            search_res = await search_svc.cognitive_search(search_query, overrides, data.language, roles)

            # Generate the answer with the LLM using the enhanced context
            answer = await self.llm_svc.generate(
                msgs,
                LLMOptions(
                    chat=ChatCompletionsOptions(
                        temperature=overrides.temperature,
                        max_tokens=self.config.chat.settings.answer.max_tokens,
                    ),
                    context_prompt=ContextPrompt(
                        template=self.config.chat.settings.answer.system_prompt,
                        data=data,
                    ),
                    enhanced_context=search_res,
                ),
            )

        except Exception as e:
            logger.error("Error while running read-retrieve-read chat approach", {"error": str(e)})
            raise

        citations = self.citation_service.get_citations(answer)

        return ChatResponse(
            answer=answer,
            keywords=search_query,
            data_points=citations,
        )

    @timer()
    def _convert_history_to_messages(self, history: List[ChatMessage], max_tokens: int) -> List[Message]:
        """_convert_history_to_messages converts the history to the internal message format.
        It also truncates the messages to the max token limit.
        """
        builder = Builder(self.llm_svc.config().gpt.model)
        current_tokens = 0

        for msg in reversed(history):
            user_tokens = builder.tokenizer.tokenize_message(Message({"role": Message.USER_ROLE, "content": msg.user}))
            bot_tokens = 0
            if msg.bot is not None:
                bot_tokens = builder.tokenizer.tokenize_message(Message({"role": Message.ASSISTANT_ROLE, "content": msg.bot}))

            if self._is_message_too_long(current_tokens + user_tokens + bot_tokens, max_tokens):
                break

            if msg.bot is not None:
                builder.add_message(Message({"role": Message.ASSISTANT_ROLE, "content": msg.bot}))
                current_tokens += bot_tokens

            builder.add_message(Message({"role": Message.USER_ROLE, "content": msg.user}))
            current_tokens += user_tokens

        logger.debug("Converted history to messages", {"num_messages": len(builder.get_messages()), "tokens": current_tokens})
        return builder.get_messages()[::-1]

    @timer()
    async def _get_chat_data(self, msgs: List[Message]) -> ChatData:
        """_get_chat_data gets the chat data from the messages of the conversation."""

        detected_lang = self.lang_svc.detect(msgs[-1].content())
        no_idea_message = self.NO_IDEA_MESSAGES.get(detected_lang)
        if no_idea_message is None:
            no_idea_message = self.NO_IDEA_MESSAGES[Language.ENGLISH]
            logger.warning(
                "Retrieved chat data with unrecognized language",
                {
                    "detected_lang": detected_lang.name,
                    "no_idea_message": no_idea_message,
                    "message": (msgs[-1].content() if LOG_SENSITIVE_DATA else "REDACTED"),
                },
            )
        else:
            logger.debug("Retrieved chat data", {"detected_lang": detected_lang.name, "no_idea_message": no_idea_message})

        return ChatData(language=detected_lang, no_idea_message=no_idea_message, injected_instructions=None)

    def _fill_overrides(self, overrides: Optional[Overrides]) -> Overrides:
        """_fill_overrides fills the overrides with the default values."""
        if overrides is None:
            return self.DEFAULT_OVERRIDES

        return overrides.fill_defaults(self.DEFAULT_OVERRIDES)

    def _is_message_too_long(self, tokens: int, max_tokens: int) -> bool:
        """_is_message_too_long checks if the message is too long."""
        return tokens + Model.ANSWER_TOKEN_LIMIT > max_tokens * 0.9
