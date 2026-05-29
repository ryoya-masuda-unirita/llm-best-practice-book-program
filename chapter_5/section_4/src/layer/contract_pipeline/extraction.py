"""
Extraction Stage Module.

The Extraction Stage is the first stage in the contract risk compliance pipeline,
responsible for:
- Parsing the raw contract text
- Extracting the document structure (chapters and sections)
- Identifying parties and contract metadata
"""

from langchain_core.runnables import RunnableConfig
from src.layer.base import BaseAgent
from src.model.model import (
    ContractChapter,
    ContractPipelineState,
    ContractSection,
    ContractStructure,
    ExtractionOutput,
    ExtractionResponse,
)
from src.prompt.prompt import (
    make_extraction_system_prompt,
    make_extraction_user_prompt,
)


class ExtractionAgent(BaseAgent):
    """
    Extraction Stage Agent (抽出ステージエージェント).

    Parses contract text and extracts structured data including chapters,
    sections, and party information.
    """

    def __init__(self):
        super().__init__(layer_name="PIPELINE", agent_name="ExtractionAgent")

    def _convert_response_to_output(self, response: ExtractionResponse, contract_id: str) -> ExtractionOutput:
        """Convert LLM response to domain output model."""
        chapters = []
        for i, ch_resp in enumerate(response.chapters):
            chapter_id = ch_resp.chapter_id or f"ch_{i + 1:02d}"
            sections = [
                ContractSection(
                    section_id=sec.section_id or f"sec_{chapter_id}_{j:02d}",
                    section_number=sec.section_number,
                    title=sec.title,
                    content=sec.content,
                    chapter_id=chapter_id,
                )
                for j, sec in enumerate(ch_resp.sections)
            ]
            chapters.append(
                ContractChapter(
                    chapter_id=chapter_id,
                    chapter_number=ch_resp.chapter_number,
                    title=ch_resp.title,
                    sections=sections,
                )
            )

        total_sections = sum(len(ch.sections) for ch in chapters)

        structure = ContractStructure(
            contract_id=contract_id,
            title=response.title,
            parties=response.parties,
            effective_date=response.effective_date,
            chapters=chapters,
            total_sections=total_sections,
        )

        return ExtractionOutput(
            structure=structure,
            extraction_notes=response.extraction_notes,
        )

    def execute(self, state: ContractPipelineState, config: RunnableConfig) -> dict:
        """Execute the extraction stage."""
        self._log_layer_start("Extracting contract structure")

        contract_input = state["contract_input"]
        self.logger.info(f"Processing contract: {contract_input.contract_id}")

        user_prompt = make_extraction_user_prompt(contract_input.raw_content)

        response = self._invoke_structured(
            config,
            make_extraction_system_prompt(),
            user_prompt,
            ExtractionResponse,
        )

        extraction_output = self._convert_response_to_output(response, contract_input.contract_id)
        self.logger.info(f"Extraction complete: {extraction_output.structure.total_sections} sections")

        all_sections = []
        for chapter in extraction_output.structure.chapters:
            all_sections.extend(chapter.sections)

        return {
            "extraction_output": extraction_output,
            "pending_sections": all_sections,
            "current_section_index": 0,
            "current_stage": "risk_scoring",
        }


def extraction_stage_node(state: ContractPipelineState, config: RunnableConfig) -> dict:
    """LangGraph node function for the Extraction Stage."""
    return ExtractionAgent().execute(state, config)
