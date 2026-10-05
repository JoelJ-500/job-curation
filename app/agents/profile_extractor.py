"""Agent 1 extraction: turn cleaned document text into a structured profile.

Uses LangChain structured output with the `CandidateProfile` Pydantic schema, so
the LLM returns typed data (missing values as `null` / empty lists) that maps
directly onto the database.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm import get_chat_model
from app.models.profile import CandidateProfile

# The design's synthesis prompt (verbatim), plus a short instruction to never
# invent data -- the schema field descriptions carry the per-attribute prompts.
SYSTEM_PROMPT = (
    "Analyze all the provided multi-format source materials, which may include "
    "resumes, text notes, code files, and visual documents or portfolio "
    "screenshots. Cross-reference and synthesize all information across these "
    "disparate sources to build a comprehensive, unified candidate profile. "
    "Ensure that skills, technical proficiencies, or project details discovered "
    "in code files or images are intelligently merged with the textual history.\n\n"
    "Rules:\n"
    "- Only use information present in the source materials. Never invent or guess data.\n"
    "- If a field cannot be determined, return null (or an empty list for collections).\n"
    "- Merge duplicates across sources into a single, best-worded entry.\n"
    "- Dates must be ISO format (YYYY-MM-DD) when known."
)

# Keep each request focused to avoid hallucination and control token cost.
MAX_CHARS_PER_DOCUMENT = 12000


def _truncate(text: str, limit: int = MAX_CHARS_PER_DOCUMENT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def build_documents_block(documents: list[tuple[str, str]]) -> str:
    """Format (file_name, text) pairs into a single labelled source block."""
    sections = []
    for file_name, text in documents:
        sections.append(f"### Source document: {file_name}\n{_truncate(text)}")
    return "\n\n".join(sections)


def extract_profile(documents: list[tuple[str, str]]) -> CandidateProfile:
    """Extract a CandidateProfile from the given (file_name, text) documents."""
    if not documents:
        return CandidateProfile()

    model = get_chat_model().with_structured_output(CandidateProfile, method="json_schema")
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_documents_block(documents)),
    ]
    result = model.invoke(messages)

    # with_structured_output returns the Pydantic instance; guard just in case.
    if isinstance(result, CandidateProfile):
        return result
    return CandidateProfile.model_validate(result)
