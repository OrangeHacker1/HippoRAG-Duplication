"""Helper for regenerate.sh — calls Claude Opus with SPEC.md and extracts generated files."""
import os
import re
import sys
import pathlib

spec_path, prompt_path, output_dir, model = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
output_dir = pathlib.Path(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)

try:
    import anthropic
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic", "-q"])
    import anthropic

spec = pathlib.Path(spec_path).read_text()
prompt_template = pathlib.Path(prompt_path).read_text()
full_prompt = prompt_template.replace("{SPEC_CONTENTS}", spec)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
print("Calling Claude Opus (this may take a minute)...")

message = client.messages.create(
    model=model,
    max_tokens=8192,
    temperature=0,
    messages=[{"role": "user", "content": full_prompt}]
)

response = message.content[0].text
(output_dir / "response.txt").write_text(response)
print(f"Response saved to {output_dir}/response.txt")

files_written = 0
for match in re.finditer(r'```(?:python)?\n# ([^\n]+\.py)\n(.*?)```', response, re.DOTALL):
    filepath = output_dir / match.group(1)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(match.group(2))
    print(f"  Written: {filepath}")
    files_written += 1

if files_written == 0:
    print("WARNING: No Python files extracted. Check reports/regenerated/response.txt manually.")
else:
    print(f"Extracted {files_written} file(s).")
