# llm/llm_client.py
import requests
from myproject.config.config_loader import load_config
from myproject.config.env_loader import load_environment


class LLMClient:
    def __init__(self):
        self.config = load_config()
        self.env = load_environment()

    """
    def generate(self, prompt: str):
        response = requests.post(
            f"{self.env['teacher_base']}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.env['teacher_key']}"
            },
            json={
                "model": self.env["teacher_model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.config["llm"]["temperature"],
                "max_tokens": self.config["llm"]["max_tokens"]
            }
        )

        return response.json()["choices"][0]["message"]["content"]
    """

    def generate(self, prompt: str):
        base_url = self.env['teacher_base'].rstrip('/')
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.env['teacher_key']}"
                },
                json={
                    "model": self.env["teacher_model"],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.config["llm"]["temperature"],
                    "max_tokens": self.config["llm"]["max_tokens"]
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            raise RuntimeError(f"LLM request failed with HTTP {status}: {e.response.text if e.response is not None else ''}")

        except requests.exceptions.ConnectionError:
            raise requests.exceptions.ConnectionError("Could not connect to LLM endpoint.")

        except requests.exceptions.Timeout:
            raise requests.exceptions.ConnectTimeout("LLM request timed out.")


    def extract_triples(self, text: str):
        prompt = f"""Extract knowledge graph triples from the text below.
Return ONLY a JSON array of [subject, relation, object] arrays. No explanation.

Example:
[["Albert Einstein", "developed", "theory of relativity"], ["theory of relativity", "is part of", "physics"]]

Text: {text}"""

        output = self.generate(prompt)

        triples = []
        try:
            start = output.index("[")
            end = output.rindex("]") + 1
            parsed = __import__("json").loads(output[start:end])
            for item in parsed:
                if isinstance(item, list) and len(item) == 3:
                    triples.append(tuple(item))
        except (ValueError, Exception):
            pass
        return triples