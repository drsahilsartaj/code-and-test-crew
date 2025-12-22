"""State definition for the multi-agent code generation system."""

from typing import TypedDict, Optional, List


class AgentState(TypedDict):
    """Central state shared across all agents."""
    
    # Prompt Refinement State
    raw_prompt: str
    refined_prompt: Optional[str]
    prompt_confirmed: bool
    refinement_history: List[str]
    
    # Code Generation State
    problem_description: str
    current_attempt: int
    max_attempts: int
    workflow_status: str  # "refining" | "in_progress" | "success" | "failed"
    generated_code: Optional[str]
    code_file_path: str
    
    # Review State
    reviewer_status: Optional[str]  # "approved" | "rejected"
    reviewer_feedback: Optional[str]
    
    # Testing State
    tester_status: Optional[str]  # "pass" | "fail"
    tester_results: Optional[str]
    
    # Flake8 Linting State
    flake8_status: Optional[str]  # "clean" | "issues"
    flake8_report: Optional[List[str]]
    
    # Metadata
    feedback_history: List[dict]
    final_result: Optional[str]


def create_initial_state(raw_prompt: str) -> AgentState:
    """Create a fresh initial state with a user prompt."""
    return AgentState(
        raw_prompt=raw_prompt,
        refined_prompt=None,
        prompt_confirmed=False,
        refinement_history=[],
        problem_description="",
        current_attempt=0,
        max_attempts=10,
        workflow_status="refining",
        generated_code=None,
        code_file_path="outputs/code.py",
        reviewer_status=None,
        reviewer_feedback=None,
        tester_status=None,
        tester_results=None,
        flake8_status=None,
        flake8_report=None,
        feedback_history=[],
        final_result=None,
    )
