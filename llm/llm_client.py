# llm/llm_client.py
import openai

class LLMClient:
    def __init__(self, model="gpt-4o-mini"):
        self.model = model

    def generate(self, prompt: str) -> str:
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response["choices"][0]["message"]["content"]

    def extract_triples(self, text: str) -> list:
        prompt = f"""
Extract knowledge graph triples from the text.

Return format:
(subject, relation, object)

Text:
{text}
"""
        output = self.generate(prompt)

        triples = []
        for line in output.split("\n"):
            if "(" in line and ")" in line:
                try:
                    triples.append(eval(line.strip()))
                except:
                    continue
        return triples