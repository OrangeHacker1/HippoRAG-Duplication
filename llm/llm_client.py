# llm/llm_client.py
import requests
from config.config_loader import load_config
from config.env_loader import load_environment


class LLMClient:
    def __init__(self):
        self.config = load_config()
        self.env = load_environment()

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

    def extract_triples(self, text: str):
        prompt = f"""
Extract triples (subject, relation, object).
Return ONLY Python tuples.

{text}
"""
        output = self.generate(prompt)

        triples = []
        for line in output.split("\n"):
            if "(" in line:
                try:
                    triples.append(eval(line.strip()))
                except:
                    continue
        return triples