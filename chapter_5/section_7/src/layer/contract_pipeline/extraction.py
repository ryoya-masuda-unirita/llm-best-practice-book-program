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
from src.model.contract_pipeline_model import (
    ContractChapter,
    ContractPipelineState,
    ContractSection,
    ContractStructure,
    ExtractionOutput,
)
from src.prompt.contract_pipeline_prompt import (
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

    def _parse_section(self, data: dict, chapter_id: str, index: int) -> ContractSection:
        """Parse a section from JSON data."""
        return ContractSection(
            section_id=data.get("section_id", f"sec_{chapter_id}_{index:02d}"),
            section_number=data.get("section_number", f"第{index + 1}条"),
            title=data.get("title", ""),
            content=data.get("content", ""),
            chapter_id=chapter_id,
        )

    def _parse_chapter(self, data: dict, index: int) -> ContractChapter:
        """Parse a chapter from JSON data."""
        chapter_id = data.get("chapter_id", f"ch_{index + 1:02d}")
        sections = [self._parse_section(s, chapter_id, i) for i, s in enumerate(data.get("sections", []))]
        return ContractChapter(
            chapter_id=chapter_id,
            chapter_number=data.get("chapter_number", f"第{index + 1}章"),
            title=data.get("title", ""),
            sections=sections,
        )

    def _parse_extraction_result(self, result: dict, contract_id: str) -> ExtractionOutput:
        """Parse the extraction result from JSON."""
        chapters = [self._parse_chapter(ch, i) for i, ch in enumerate(result.get("chapters", []))]

        total_sections = sum(len(ch.sections) for ch in chapters)

        structure = ContractStructure(
            contract_id=contract_id,
            title=result.get("title", "不明な契約書"),
            parties=result.get("parties", []),
            effective_date=result.get("effective_date", ""),
            chapters=chapters,
            total_sections=total_sections,
        )

        return ExtractionOutput(
            structure=structure,
            extraction_notes=result.get("extraction_notes", ""),
        )

    def execute(self, state: ContractPipelineState, config: RunnableConfig) -> dict:
        """Execute the extraction stage."""
        self._log_layer_start("Extracting contract structure")

        contract_input = state["contract_input"]
        self.logger.info(f"Processing contract: {contract_input.contract_id}")

        user_prompt = make_extraction_user_prompt(contract_input.raw_content)

        try:
            result = self._invoke_and_parse(config, make_extraction_system_prompt(), user_prompt)
            extraction_output = self._parse_extraction_result(result, contract_input.contract_id)

            self.logger.info(f"Extraction complete: {extraction_output.structure.total_sections} sections")

            # Flatten all sections for the next stage
            all_sections = []
            for chapter in extraction_output.structure.chapters:
                all_sections.extend(chapter.sections)

            return {
                "extraction_output": extraction_output,
                "pending_sections": all_sections,
                "current_section_index": 0,
                "current_stage": "risk_scoring",
            }

        except (KeyError, ValueError) as e:
            self._handle_parse_error(e)
            raise ValueError(f"Extraction stage failed: {e}")


def extraction_stage_node(state: ContractPipelineState, config: RunnableConfig) -> dict:
    """LangGraph node function for the Extraction Stage."""
    return ExtractionAgent().execute(state, config)
