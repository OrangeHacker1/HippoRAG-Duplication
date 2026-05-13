# llm/llm_client.py
import requests
from myproject.config.config_loader import load_config
from myproject.config.env_loader import load_environment


class LLMClient:
    def __init__(self):
        self.config = load_config()
        self.env = load_environment()


    def generate(self, prompt: str):
        base_url = self.env['teacher_base'].rstrip('/')
        max_retries = self.config["llm"].get("retries", 3)
        last_exception = None
        for attempt in range(1, max_retries + 1):
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
                    timeout=self.config["llm"]["timeout"]
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]

            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                #raise RuntimeError(f"LLM request failed with HTTP {status}: {e.response.text if e.response is not None else ''}")

            except requests.exceptions.ConnectionError:
                #raise requests.exceptions.ConnectionError("Could not connect to LLM endpoint.")
                last_exception = requests.exceptions.ConnectionError(
                f"Could not connect to LLM endpoint (attempt {attempt}/{max_retries})."
            )

            except requests.exceptions.Timeout:
                #raise requests.exceptions.ConnectTimeout("LLM request timed out.")
                last_exception = requests.exceptions.ConnectTimeout(
                f"LLM request timed out (attempt {attempt}/{max_retries})."
            )
                
        # All attempts exhausted — raise the last recorded exception
        raise last_exception    


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