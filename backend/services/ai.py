import re
import google.generativeai as genai


def generate_content_with_fallback(
    prompt: str, api_key: str, generation_config=None
) -> tuple[str, str]:
    """
    Try available Gemini models in priority order.
    Returns (response_text, model_name) or (error_message, "Error").
    Exact logic from original app.py.
    """
    try:
        genai.configure(api_key=api_key)
        try:
            models = genai.list_models()
            available_models = [
                m.name for m in models
                if "generateContent" in m.supported_generation_methods
            ]
        except Exception:
            available_models = ["gemini-1.5-pro", "gemini-1.5-flash"]

        priority_order = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]
        sorted_models = sorted(
            available_models,
            key=lambda m: next(
                (i for i, p in enumerate(priority_order) if p in m),
                len(priority_order),
            ),
        )

        errors = []
        for model_name in sorted_models:
            if "embedding" in model_name:
                continue
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt, generation_config=generation_config
                )
                return response.text, model_name
            except Exception as e:
                errors.append(f"{model_name}: {str(e)}")

        return f"All models failed. {'; '.join(errors)}", "Error"
    except Exception as e:
        return f"Unexpected Error: {str(e)}", "Error"


def split_analysis(text: str) -> tuple[str, str]:
    """
    Split combined analysis text into (module_analysis, risk_map).
    Uses <<<SEP>>> token first, then falls back to regex heading split.
    """
    if "<<<SEP>>>" in text:
        p1, p2 = text.split("<<<SEP>>>", 1)
        return p1.strip(), p2.strip()

    # Fallback split if AI forgot the separator token
    split_match = re.split(
        r'(?:\n##\s*(?:(?:2\.)?\s*RISK MAP).*|\n#\s*(?:(?:2\.)?\s*RISK MAP).*)',
        text, 1, flags=re.IGNORECASE,
    )
    if len(split_match) == 2:
        mod_text = split_match[0].strip()
        risk_text = "## RISK MAP\n" + split_match[1].strip()
        return mod_text, risk_text

    return text, ""
