import modal

app = modal.App("my-llama-3-endpoint")

# Use a newer, stable vLLM version (0.4.2) directly from DockerHub to avoid PyTorch crashes
vllm_image = modal.Image.from_registry(
    "vllm/vllm-openai:v0.4.2",
    add_python="3.10"
).pip_install("hf-transfer==0.1.6").env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})

# Using an ungated Llama 3 model so it doesn't crash asking for HuggingFace Tokens
MODEL_NAME = "NousResearch/Meta-Llama-3-8B-Instruct"

@app.function(
    image=vllm_image,
    gpu="A10G",
    allow_concurrent_inputs=100,
    timeout=60 * 60,
    keep_warm=1,
)
@modal.web_server(8000, startup_timeout=600)
def serve():
    import subprocess
    print("Starting vLLM OpenAI-Compatible Server...")
    subprocess.run([
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", MODEL_NAME,
        "--served-model-name", "modal-model", # Maps the endpoint strictly to modal-model
        "--port", "8000",
        "--max-model-len", "4096",
        "--host", "0.0.0.0"
    ])
