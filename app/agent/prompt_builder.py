from app.agent.classifier import TaskType

PROMPT_TEMPLATES: dict[TaskType, str] = {
    TaskType.API_DESIGN: (
        "You are a backend API design expert.\n"
        "Design a REST API based on the following requirement.\n"
        "Return a JSON object with keys: task_type, summary, assumptions, result, risks, confidence.\n"
        "The result should contain: endpoint, request_schema, response_example, naming_conventions.\n\n"
        "Requirement: {user_input}"
    ),
    TaskType.DEPLOYMENT_CHECKLIST: (
        "You are a deployment engineering expert.\n"
        "Generate a deployment checklist based on the following context.\n"
        "Return a JSON object with keys: task_type, summary, assumptions, result, risks, confidence.\n"
        "The result should contain: pre_deployment, env_check, rollback_plan, monitoring.\n\n"
        "Context: {user_input}"
    ),
    TaskType.CODE_REVIEW: (
        "You are a senior code reviewer.\n"
        "Review the following code for consistency and best practices.\n"
        "Return a JSON object with keys: task_type, summary, assumptions, result, risks, confidence.\n"
        "The result should contain: issues (list of objects with severity, type, description, suggestion).\n\n"
        "Code: {user_input}"
    ),
    TaskType.ERROR_ANALYSIS: (
        "You are an error analysis expert.\n"
        "Analyze the following error and provide diagnosis.\n"
        "Return a JSON object with keys: task_type, summary, assumptions, result, risks, confidence.\n"
        "The result should contain: suspected_cause, troubleshooting_steps, recommended_fix.\n\n"
        "Error: {user_input}"
    ),
}


def build_prompt(task_type: TaskType, user_input: str) -> str:
    template = PROMPT_TEMPLATES[task_type]
    return template.format(user_input=user_input)
