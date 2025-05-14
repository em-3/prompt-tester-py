import argparse
import logging
import openai
import textwrap
import time
import tomllib
import traceback

from log_format import CustomFormatter
from pathlib import Path

logger = logging.Logger(__name__)
logger.setLevel(logging.DEBUG)

con_handler = logging.StreamHandler()
con_handler.setLevel(logging.INFO)

con_handler.setFormatter(CustomFormatter())

logger.addHandler(con_handler)

def prep_completion(client: openai.OpenAI, messages: list[dict[str, str]], seed: int, model: str, max_tokens: int, generation_options: dict[str] = None, stream: bool = False):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        seed=seed,
        max_completion_tokens=max_tokens,
        stream=stream,
        extra_body=generation_options
    )

def generate(client: openai.OpenAI, messages: str, seed: int, max_tokens: int, model_name: str = "gpt-3.5-turbo",  generation_options: dict[str] = None):
    return prep_completion(client, messages, seed, model_name, max_tokens, generation_options).choices[0].message.content

def generate_stream(client: openai.OpenAI, messages: str, seed: int, max_tokens: int, model_name: str = "gpt-3.5-turbo", generation_options: dict[str] = None):
    for chunk in prep_completion(client, messages, seed, model_name, max_tokens, generation_options, True):
        yield chunk.choices[0].delta.content or ""

def stream_output(client: openai.OpenAI, model_name: str, options: dict, messages: list[dict[str, str]], max_tokens: int, generation_options: dict[str], start_time: int):
    thinking_started = False
    thinking_animation_frame = 0
    final_result = ""
    CLEAR_LINE = "\033[2K\033[1G"  # ANSI escape code for clearing the line

    for token in generate_stream(client, messages, options.seed, max_tokens, model_name, generation_options):
        if options.hide_thinking_tokens:
            if not thinking_started:
                idx = token.find("<think>")
                print_part = token[:idx] if idx != -1 else token
                print(print_part, end="", flush=True)
                if idx != -1:
                    thinking_started = True
            else:
                idx = token.find("</think>")
                if idx != -1:
                    thinking_started = False
                    elapsed = time.time() - start_time
                    print(f"{CLEAR_LINE}Thought for {elapsed:.2f} seconds ({elapsed/60:.2f} minutes).\n", end="", flush=True)
                else:
                    dots = "." * thinking_animation_frame
                    print(f"{CLEAR_LINE}Thinking{dots}", end="", flush=True)
                    thinking_animation_frame = 0 if thinking_animation_frame >= 3 else thinking_animation_frame + 1
        else:
            print(token, end="", flush=True)
        
        final_result += token  # Accumulate token regardless of conditions
        
    return final_result

def print_output(client: openai.OpenAI, model_name: str, options: dict, messages: list[dict[str, str]], max_tokens: int, generation_options: dict[str]):
    final_result = output = generate(client, messages, options.seed, max_tokens, model_name, generation_options)
    
    # Remove thinking tokens if present
    if options.hide_thinking_tokens:
        output = output[:output.find("<think>\n")] + output[output.find("\n</think>") + 9:]

    print(output)

    return final_result

def execute_model(client: openai.OpenAI, model_name: str, messages: list[dict[str, str]], max_tokens: int, options: dict = None, generation_options: dict = None, friendly_name: str = None):
    try:
        logger.info(f"Starting generation for {friendly_name}.")

        start_time = time.time()

        final_result = ""
        
        if options.silent:
            final_result = generate(client, messages, options.seed, max_tokens, model_name, generation_options)
        else:
            print(f"Response for config: {friendly_name}\n")
            if options.stream:
                final_result = stream_output(client, model_name, options, messages, max_tokens, generation_options, start_time)
            else:
                final_result = print_output(client, model_name, options, messages, max_tokens, generation_options)
            print()

        time_elapsed = time.time() - start_time
        time_minutes = time_elapsed / 60
        
        logger.info(f"Generation took {time_elapsed:.2f} seconds ({time_minutes:.2f} minutes).")

        if options.save_output != "none":
            # Remove thinking tokens if present
            if options.save_output == "user-only":
                final_result = final_result[:final_result.find("<think>")] + final_result[final_result.find("</think>") + 8:]

            # Write the remaining output to the file
            with Path(f"./outputs/{friendly_name}.md").open("w", encoding="utf-8") as output_file:
                output_file.write(final_result.strip())
            
            logger.info(f"Output saved to outputs/{friendly_name}.md")

    except KeyboardInterrupt:
        print()

        logger.info("Keyboard interrupt detected. Cancelling execution.")
        exit(0)
    except:
        print()

        logger.debug(traceback.format_exc())
        logger.error("An error occurred while streaming the response. Skipping to next config.")

def parse_args():
    parser = argparse.ArgumentParser(
        prog="Dynamic Prompt Tester Tool",
        description="Automated prompt testing with support for any OpenAI-compatible backend",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "-c",
        "--config",
        help="a path to the location of the application's config file",
        default="config.toml",
        dest="config_path"
    )
    parser.add_argument(
        "-p",
        "--prompt",
        help="a path to a TOML file containing a prompt to run",
        default=None,
        dest="prompt"
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="include debug messages in log",
        action="store_true",
        default=False,
        dest="debug"
    )
    parser.add_argument(
        "--seed",
        help="the seed to use when generating the output",
        default=3333,
        dest="seed"
    )
    parser.add_argument(
        "--max-tokens",
        help="the maximum number of tokens to generate",
        default=512,
        dest="max_tokens"
    )

    output_opts = parser.add_argument_group("output options")
    exclusive_output_opts = output_opts.add_mutually_exclusive_group()
    exclusive_output_opts.add_argument(
        "-s",
        "--stream",
        help="stream the response from the server in real time",
        action="store_true",
        default=False,
        dest="stream"
    )
    exclusive_output_opts.add_argument(
        "--silent",
        help="suppress model output",
        action="store_true",
        default=False,
        dest="silent"
    )
    output_opts.add_argument(
        "--save",
        help="save part or all of the output to a file" + textwrap.dedent("""
            options:
                none      - do not save any output
                all       - save all outputs
                user-only - save only the user-facing output, ignoring thinking tokens
        """),
        choices=("none", "all", "user-only"),
        default="none",
        const="all",
        nargs="?",
        dest="save_output"
    )

    thinking_opts = parser.add_argument_group("thinking options")
    thinking_opts.add_argument(
        "-t",
        "--hide-thinking",
        help="hide the thinking tokens for the model",
        action="store_true",
        default=False,
        dest="hide_thinking_tokens"
    )

    return parser.parse_args()

def load_config(config_path: Path):
    if not config_path.exists():
        logger.critical(f"Config file at '{config_path.absolute().as_posix()}' does not exist.")
        exit(-1)

    config = {}

    try:
        with config_path.open("rb") as file:
            config = tomllib.load(file)
    except tomllib.TOMLDecodeError:
        logger.critical(f"Config '{config_path.absolute().as_posix()}' does not have a valid TOML structure.")
        exit(-1)
    except:
        logger.debug(traceback.format_exc())
        logger.critical(f"An error occurred while reading the config.")
        exit(-1)

    if "servers" not in config or "models" not in config or "executions" not in config:
        logger.critical(f"One or more required fields are missing from your config.toml. Please ensure that you have at least defined one server, one model, and an execution configuration")
        exit(-1)

    return config

def initialize_clients(servers: dict[str, dict[str]]):
    clients = {}

    for id, server in servers.items():
        clients[id] = openai.OpenAI(base_url=server["base_url"], api_key=server["key"])

    return clients

def load_prompt_from_file(prompt_path: Path):
    if not prompt_path.exists():
        logger.critical(f"Prompt file at '{prompt_path.absolute().as_posix()}' does not exist.")
        exit(-1)

    prompt_data = {}

    try:
        with prompt_path.open("rb") as file:
            prompt_data = tomllib.load(file)
    except tomllib.TOMLDecodeError:
        logger.critical(f"Prompt file '{prompt_path.absolute().as_posix()}' does not have a valid TOML structure.")
        exit(-1)
    except:
        logger.debug(traceback.format_exc())
        logger.critical(f"An error occurred while reading the prompt file.")
        exit(-1)

    messages = []

    sys_prompt = ""

    if "sys_prompt" in prompt_data:
        sys_prompt = prompt_data["sys_prompt"]
    else:
        logger.warning("The prompt file is missing the system prompt. This may cause unintended behavior.")

    sys_prompt += f'\n{prompt_data["aux_info"]}' if "aux_info" in prompt_data else ""
    
    if sys_prompt:
        messages.append({"role": "system", "content": sys_prompt})

    if "author_note" in prompt_data:
        messages.append({"role": "user", "content": prompt_data["author_note"]})

    if "user_prompt" in prompt_data:
        messages.append({"role": "user", "content": prompt_data["user_prompt"]})
    else:
        logger.warning("The prompt file is missing the user prompt. This may cause unintended behavior.")

    logger.debug(messages)

    if len(messages) == 0:
        logger.critical("All prompt components were missing.")
        exit(-1)

    return messages

def main():
    args = parse_args()

    if args.debug:
        con_handler.setLevel(logging.DEBUG)

    logger.info("Initializing client")

    logger.info("Loading config")

    config = load_config(Path(args.config_path))

    logger.debug(f"Raw config: {config}")

    clients = initialize_clients(config["servers"])

    prompt_path = args.prompt or config["prompt"] or None

    if not prompt_path:
        logger.critical("Prompt file missing. Please specify a prompt file in the config or via the --prompt option.")
        exit(-1)
    
    messages = load_prompt_from_file(Path(prompt_path))

    for execution in config["executions"]:
        key = execution["model"]
        if key not in config["models"]:
            logger.error(f"Model '{key}' does not exist! Skipping...")
            continue

        model = config["models"][key]

        gen_opts = None

        if "gen_opts" in execution:
            key = execution["gen_opts"]
            if key in config["gen_opts"]:
                gen_opts = config["gen_opts"][key]
            else:
                logger.error(f"Generation options '{key}' does not exist! Using default options...")

        execute_model(client=clients[model["server"]], model_name=model["model_id"], friendly_name=model["friendly_name"], messages=messages, max_tokens=args.max_tokens, options=args, generation_options=gen_opts)

if __name__ == "__main__":
    main()