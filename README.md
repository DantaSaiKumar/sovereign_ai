# Sovereign AI Workbench
**Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs for Confidential Industrial Work**

A Windows-first, local-only prototype for confidential industrial document analysis. The target development machine is an ASUS TUF Gaming A15 running Windows 11, with 8 GB system RAM and an NVIDIA RTX 3050 laptop GPU.

## What is implemented

- Local Ollama inference with a localhost-only endpoint guard
- Small-model routing: Qwen 2.5 1.5B for text; optional Moondream for images
- PDF, DOCX, TXT, Markdown, CSV, XLSX and image ingestion
- Local chunking and lightweight BM25-style retrieval (no cloud embeddings/vector server)
- Evidence-linked agent workflow with explicit uncertainty and human-review status
- Deterministic numeric threshold/range checks and document-condition follow-up flags
- Citation checks that withhold unsupported or contradictory model statements
- Approved arithmetic and CSV tools; no arbitrary shell/Python execution
- SQLite persistence for documents, chunks, tasks, approvals and audit events
- SHA-256 tamper-evident audit chain
- DOCX, XLSX and PPTX report generation
- Streamlit interface, optional local access key
- Offline unit/integration tests using a fake model client

## Target hardware and model strategy

- OS: Windows 11 64-bit
- System memory: 8 GB RAM
- GPU: NVIDIA RTX 3050 laptop GPU (VRAM differs by laptop configuration; check Task Manager → Performance → GPU or run `nvidia-smi`)
- Text model: `qwen2.5:1.5b`
- Optional vision model: `moondream`, pulled and used only when image analysis is needed
- Ollama: native Windows application; NVIDIA acceleration is supported when the NVIDIA driver is compatible

**Memory policy:** Keep one model loaded at a time, use a 2,048-token context for text and 1,536 for image analysis, and unload after each request. The RTX 3050 can accelerate inference, but 8 GB system RAM remains a constraint. Do not assume the whole model will fit in GPU VRAM; Ollama may split work between GPU and system memory/CPU. Close browsers, games and other memory-heavy programs during inference. If the system becomes unstable, use CPU mode or reduce model/context size.

Ollama's current GPU documentation lists RTX 3050 as supported and specifies NVIDIA driver requirements. See [Ollama Windows documentation](https://docs.ollama.com/windows) and [Ollama GPU support](https://docs.ollama.com/gpu).

## Install on Windows 11

1. Install **Python 3.11 or newer** from [python.org](https://www.python.org/downloads/windows/). Enable the option to add Python to PATH (or install the Python launcher).
2. Install the current **NVIDIA Game Ready or Studio driver** for the laptop from [NVIDIA](https://www.nvidia.com/Download/index.aspx), then restart Windows.
3. Install **Ollama for Windows** from [ollama.com/download](https://ollama.com/download). It runs as a native Windows application; WSL is not required.
4. Extract this project ZIP to a normal folder, for example `C:\SovereignAI`.
5. Right-click `run_windows.bat` and choose **Run**, or open PowerShell in the project folder and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run_windows.ps1
```

The launcher creates `.venv`, installs dependencies, checks/starts the local Ollama API, downloads `qwen2.5:1.5b`, checks NVIDIA visibility, and starts Streamlit at `http://127.0.0.1:8501`.

The first model download requires internet access. After the model has downloaded, inference runs locally. Do not expose the Streamlit or Ollama ports to your LAN or the public internet.

### Optional image understanding

After the text workflow is working, open PowerShell and run:

```powershell
ollama pull moondream
```

Use image analysis only when required. Do not keep the vision model resident alongside the text model. If `moondream` does not fit comfortably on the particular RTX 3050/system configuration, skip image analysis or use a smaller compatible vision model after testing.

### Confirm GPU use

In a second PowerShell window:

```powershell
nvidia-smi
ollama ps
```

Run a short prompt in the app while checking `nvidia-smi`. `ollama ps` reports the processor allocation for the loaded model in supported Ollama versions. If it shows CPU-only, update the NVIDIA driver, restart Ollama, and check its logs. GPU acceleration is not guaranteed merely because the GPU is present.

### Optional OCR

Image OCR is optional. Install Tesseract for Windows from its official project distribution and then, inside the activated environment, install `pytesseract`:

```powershell
.\.venv\Scripts\python.exe -m pip install pytesseract
```

Scanned PDF OCR is not currently automatic; convert pages to images and ingest them individually or add a reviewed OCR pipeline.

## Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests use a fake model client and do not require downloading a model or having Ollama running.

## Temporary local workflow trace

For troubleshooting, set `SOVEREIGN_DEBUG_TRACE=1` before starting the app. Structured task inputs, selected documents, retrieved excerpts, prompts, raw model responses, verification results and displayed answers are appended to `data/debug_trace.jsonl`. Tracing is off by default and stays in the configured local data directory; because traces can contain confidential document text, disable tracing and remove the file when debugging is complete.

## Security and deployment boundaries

- The app binds to `127.0.0.1` by default.
- The Ollama client rejects non-local hostnames/IPs.
- No public AI API keys or external AI endpoints are used for inference.
- Uploaded files are size/type checked and stored in the local `data/` directory.
- The calculator uses a restricted AST evaluator.
- Arbitrary generated code and shell commands are deliberately not executed.
- Audit events are linked with SHA-256 hashes.
- Human review is mandatory in the workflow; an approval record is not a regulatory certification.
- The launcher limits Ollama to one loaded model and one parallel request when it starts the Ollama process itself. If the Ollama desktop app was already running, its existing process settings remain in effect; the model requests still ask Ollama to unload each model after use.

**Important:** localhost binding and an application-level URL guard are not proof of a whole-machine air gap. For production, enforce outbound network restrictions with Windows Defender Firewall/network controls, use separate OS accounts, encrypted storage, backups, secrets management, vulnerability review, and independent outbound-traffic monitoring. Do not connect this prototype directly to SCADA/DCS or operational control systems.

## Current limitations

- Retrieval is lexical BM25-style ranking, not semantic vector search. This is an intentional memory-saving first implementation.
- Vision is optional and requires the Moondream model; it is not automatically called by the standard text workflow.
- OCR is optional and scanned PDFs need a dedicated OCR pass.
- Authentication is an optional shared local access key, not enterprise SSO/RBAC.
- The agent is a bounded sequential workflow, not a fully autonomous unrestricted multi-agent system.
- No fine-tuning is performed. A LoRA/QLoRA training pipeline should be a separate offline stage and requires suitable training hardware.
- Industrial findings are decision-support drafts only and must be validated by qualified personnel.
- Verification separates document-grounded findings from real-world inspection; synthetic records do not establish actual equipment condition. Citation support checks are conservative lexical checks, not semantic proof.
- Actual latency, VRAM allocation and stability must be tested on the exact RTX 3050 variant and driver installed on the target laptop.

## Project structure

```text
app.py
sovereign/
  config.py db.py security.py audit.py
  ingestion.py retrieval.py models.py tools.py
  agent.py reports.py
tests/
run_windows.ps1
run_windows.bat
requirements.txt
```
