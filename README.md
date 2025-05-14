# Prompt Tester

Test the same prompt with multiple models/providers/settings using a simple TOML file.

# Getting Started

## Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/)

## Installing

Clone this repo and install the required packages.

```bash
git clone https://github.com/em-3/prompt-tester-py
uv sync
```

## Configuration

This tool pulls all its options from a file named `config.toml`. It looks for this file in the working directory by default, but this can be changed using the `--config` option.

A config file looks something like this:

```toml
# config.toml

# List multiple different execution options - mix models and generation options. The script will attempt to run them in the order listed.
executions = [
    { model = "gemma-3-4b", gen_opts = "gemma3" },
    { model = "gemma-3-12b", gen_opts = "gemma3" },
    { model = "gemma-3-27b", gen_opts = "gemma3" },
    { model = "qwen-3-8b" },
    { model = "qwen-3-30b-moe" },
    { model = "qwen-3-32b" },
    { model = "gemini-2_0-flash" },
]

# Optionally, add a default prompt file that will be used when running without arguments
prompt = "prompts/summarize-task.toml"

# Add any OpenAI-compatible server
[servers]
[servers.gemini]
base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
key = "your-key-here"

# Works with locally hosted models as long as they support OpenAI's API
[servers.llama-swap]
base_url = "http://localhost:8000/v1"
key = "no-key" # Key is always required due to the OpenAI Python package

# Define reusable generation options
[gen_opts]
[gen_opts.default] # Optional default parameters
temperature = 0.7
min_p = 0.1
top_k = 40
top_p = 0.5

[gen_opts.gemma3]
temperature = 1.0
min_p = 0.0
top_k = 64
top_p = 0.95
rep_pen = 1.0

# Define available models
[models]
[models.gemini-2_0-flash]
model_id = "gemini-2.0-flash" # Set the upstream model id
friendly_name = "Gemini 2.0 Flash" # Give a friendly name that will show up in logs and be used to name saved output files
server = "gemini" # Define which server this model is reachable at

[models.gemma-3-4b]
model_id = "gemma-3-4b"
friendly_name = "Gemma 3 4B"
server = "llama-swap"

[models.gemma-3-12b]
model_id = "gemma-3-12b"
friendly_name = "Gemma 3 12B"
server = "llama-swap"

[models.gemma-3-27b]
model_id = "gemma-3-27b"
friendly_name = "Gemma 3 27B"
server = "llama-swap"

[models.qwen-3-8b]
model_id = "qwen-3-8b"
friendly_name = "Qwen 8B"
server = "llama-swap"

[models.qwen-3-30b-moe]
model_id = "qwen-3-30b-moe"
friendly_name = "Qwen 30B MOE"
server = "llama-swap"

[models.qwen-3-32b]
model_id = "qwen-3-32b"
friendly_name = "Qwen 32B"
server = "llama-swap"
```

## Prompt Files

You need to define at least one prompt file to use this tool. All prompt files follow the same format:

```toml
# prompt.toml

# The system prompt for the model
sys_prompt = "System prompt goes here."

# An optional field that will be injected as a user message after the system prompt. Use it to include extra system context that doesn't fit into the system prompt (e.g., world info for story prompts).
aux_info = "Auxiliary info goes here."

# An optional field that will be injected as a user message after the system prompt. Use it to include any extra context that might not fit into the system or auxiliary info fields.
author_note = "Author's note goes here."

# The primary user prompt
user_prompt = "User prompt goes here."
```

## Running

You can run the tool using the following command:

```bash
uv run prompt-tester.py --prompt path/to/your/prompt/file.toml
```

If you defined a prompt path in your config file, you may omit the `--prompt` flag.

The output will be displayed when the generation is finished. If your endpoints support streaming, you can add `--stream` to view the output in real time. To save generated outputs, add the `--save` flag. This will save each output as a Markdown file in the `./outputs` directory.

You can see all the available options by running the above command with the `--help` flag. Note that options specified in the terminal will override equivalent options from the config file.
