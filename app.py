import json, os
from pathlib import Path
import streamlit as st
from sovereign.config import APP_NAME, REPORT_DIR, ensure_dirs, GENERAL_MODEL, VISION_MODEL
from sovereign.db import init_db, list_documents, list_tasks, get_task, list_approvals
from sovereign.ingestion import ingest_bytes
from sovereign.models import LocalModelClient, ModelUnavailable
from sovereign.agent import run_workflow, record_human_decision
from sovereign.tools import calculate, summarize_csv_bytes
from sovereign.audit import verify_chain, recent_events
from sovereign.reports import generate_docx, generate_xlsx, generate_pptx

st.set_page_config(page_title=APP_NAME, page_icon="🛡️", layout="wide")
ensure_dirs()
init_db()

# Optional local access gate. Set SOVEREIGN_ACCESS_KEY before starting Streamlit.
access_key = os.getenv("SOVEREIGN_ACCESS_KEY", "")
if access_key:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🛡️ Sovereign AI Workbench")
        entered = st.text_input("Local access key", type="password")
        if st.button("Unlock"):
            if entered == access_key:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid access key.")
        st.stop()

st.title("🛡️ Sovereign AI Workbench")
st.caption("Local-first industrial knowledge assistant · Windows 11 · RTX 3050 · 8 GB system RAM")
client = LocalModelClient()
models = client.list_models()
m1, m2, m3 = st.columns(3)
m1.metric("Local inference", "Online" if models else "Offline")
m2.metric("Documents indexed", len(list_documents()))
m3.metric("Registered local models", len(models))
st.caption("Model runtime is restricted to localhost. The application does not call public AI APIs.")

tab_chat, tab_docs, tab_tools, tab_review, tab_audit = st.tabs(
    ["Agent Workspace", "Knowledge Base", "Local Tools", "Human Review & Reports", "Security Audit"]
)

with tab_chat:
    st.subheader("Industrial task workspace")
    st.write("Example: Compare the uploaded pump inspection report with the internal maintenance SOP and prepare evidence-backed findings.")
    docs = list_documents()
    selected = st.multiselect("Use documents", options=[d["id"] for d in docs],
                              format_func=lambda x: next((d["filename"] for d in docs if d["id"] == x), x))
    question = st.text_area("Describe the task", height=120,
                            placeholder="Audit the uploaded equipment records against the internal procedure...")
    if st.button("Run local agent workflow", type="primary", disabled=not question.strip()):
        st.session_state.pop("last_task_id", None)
        with st.spinner("Retrieving local evidence and running the selected local model..."):
            try:
                result = run_workflow(question.strip(), selected or None, client=client)
                st.session_state.last_task_id = result["task_id"]
                st.success(f"Workflow completed. Task ID: {result['task_id']}")
            except ModelUnavailable as exc:
                st.error(str(exc))
                st.info(f"Install the recommended model with: ollama pull {GENERAL_MODEL}")
            except Exception as exc:
                st.exception(exc)
    task_id = st.session_state.get("last_task_id")
    if task_id:
        task = get_task(task_id)
        if task and task.get("answer"):
            st.caption(f"Saved result for task {task_id}: {task['question']}")
            st.markdown("### Analysis")
            st.markdown(task["answer"])
            verification = json.loads(task.get("verification") or "{}")
            st.warning("Human review required. AI output is not an operational authorization.")
            with st.expander("Verification details"):
                st.json(verification)
            st.markdown("### Evidence")
            for src in json.loads(task.get("sources_json") or "[]"):
                with st.expander(f"[{src['id']}] {src['filename']} · page {src.get('page') or 'N/A'}"):
                    st.write(src["excerpt"])

with tab_docs:
    st.subheader("Confidential local document library")
    uploaded = st.file_uploader("Upload PDF, DOCX, TXT, MD, CSV, XLSX or image",
                                type=["pdf", "docx", "txt", "md", "csv", "xlsx", "png", "jpg", "jpeg", "webp"],
                                accept_multiple_files=True)
    if st.button("Ingest selected files", disabled=not uploaded):
        for item in uploaded:
            try:
                doc, count = ingest_bytes(item.name, item.getvalue())
                st.success(f"Indexed {doc['filename']} — {count} chunks")
            except Exception as exc:
                st.error(f"{item.name}: {exc}")
    st.markdown("### Indexed documents")
    docs = list_documents()
    if docs:
        st.dataframe([{"Filename": d["filename"], "Type": d["file_type"],
                       "Status": d["status"], "SHA-256": d["sha256"][:16] + "…",
                       "Added": d["created_at"]} for d in docs], use_container_width=True)
    else:
        st.info("No documents indexed yet.")
    st.caption("Scanned PDFs may require local OCR. Install Tesseract separately if OCR is needed; OCR support is optional.")
    image_docs = [d for d in docs if d["file_type"] in {".png", ".jpg", ".jpeg", ".webp"}]
    if image_docs:
        st.markdown("### On-demand local vision analysis")
        image_id = st.selectbox("Choose an image", [d["id"] for d in image_docs],
                                format_func=lambda x: next((d["filename"] for d in image_docs if d["id"] == x), x))
        vision_prompt = st.text_input("Vision task", value="Describe the visible equipment, labels, gauges and any apparent anomalies. Separate observations from uncertainty.")
        if st.button("Analyze image with local vision model"):
            selected_doc = next(d for d in image_docs if d["id"] == image_id)
            try:
                with open(selected_doc["stored_path"], "rb") as image_file:
                    vision_text, vision_model = client.describe_image(image_file.read(), vision_prompt)
                st.session_state.last_vision_result = (vision_text, vision_model)
                from sovereign.audit import append_event
                append_event("local_vision_analysis", {"document_id": image_id, "model": vision_model})
            except ModelUnavailable as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(str(exc))
        if st.session_state.get("last_vision_result"):
            vision_text, vision_model = st.session_state.last_vision_result
            st.caption(f"Model: {vision_model} · local inference")
            st.write(vision_text)
            st.warning("Visual observations are preliminary. Confirm equipment identity and conditions against approved engineering records.")

with tab_tools:
    st.subheader("Approved local tools")
    with st.expander("Restricted arithmetic calculator", expanded=True):
        expression = st.text_input("Arithmetic expression", placeholder="(1250 * 0.08) + 45")
        if st.button("Calculate"):
            try:
                st.success(f"Result: {calculate(expression)['result']}")
            except Exception as exc:
                st.error(str(exc))
    with st.expander("CSV telemetry summary"):
        csv_file = st.file_uploader("Select CSV", type=["csv"], key="csv_tool")
        if csv_file and st.button("Summarize CSV"):
            try:
                st.json(summarize_csv_bytes(csv_file.getvalue()))
            except Exception as exc:
                st.error(str(exc))
    st.info("Arbitrary shell commands and arbitrary generated Python are intentionally not exposed. Industrial execution requires separately configured, reviewed tools.")

with tab_review:
    st.subheader("Human approval and deliverables")
    tasks = list_tasks()
    completed = [t for t in tasks if t["status"] == "completed"]
    if not completed:
        st.info("No completed tasks are awaiting review.")
    else:
        chosen = st.selectbox("Select task", [t["id"] for t in completed],
                              format_func=lambda x: next((t["question"][:90] for t in completed if t["id"] == x), x))
        task = get_task(chosen)
        sources = json.loads(task.get("sources_json") or "[]")
        verification = json.loads(task.get("verification") or "{}")
        st.write(task["answer"])
        reviewer = st.text_input("Reviewer name / role")
        note = st.text_area("Review note")
        c1, c2, c3 = st.columns(3)
        if c1.button("Approve draft"):
            try:
                record_human_decision(chosen, "approved", reviewer, note)
                st.success("Approval decision recorded in the audit log.")
            except Exception as exc:
                st.error(str(exc))
        if c2.button("Reject draft"):
            try:
                record_human_decision(chosen, "rejected", reviewer, note)
                st.success("Rejection recorded.")
            except Exception as exc:
                st.error(str(exc))
        if c3.button("Needs revision"):
            try:
                record_human_decision(chosen, "needs_revision", reviewer, note)
                st.success("Revision request recorded.")
            except Exception as exc:
                st.error(str(exc))
        approvals = list_approvals(chosen)
        if approvals:
            st.dataframe(approvals, use_container_width=True)
        st.markdown("#### Generate deliverables")
        if st.button("Generate DOCX / XLSX / PPTX"):
            try:
                paths = [generate_docx(task, sources, verification, approvals[0] if approvals else None),
                         generate_xlsx(task, sources, verification),
                         generate_pptx(task, sources, verification)]
                st.session_state.report_paths = [str(p) for p in paths]
                st.success("Reports generated locally.")
            except Exception as exc:
                st.exception(exc)
        for p in st.session_state.get("report_paths", []):
            path = Path(p)
            if path.exists():
                st.download_button(f"Download {path.suffix.upper()} — {path.name}",
                                   data=path.read_bytes(), file_name=path.name)

with tab_audit:
    st.subheader("Security and audit integrity")
    valid, count = verify_chain()
    st.metric("Audit chain entries", count)
    if valid:
        st.success("SHA-256 audit chain integrity check passed.")
    else:
        st.error(f"Audit chain integrity failure at entry {count}.")
    st.markdown("### Recent events")
    st.dataframe(recent_events(50), use_container_width=True)
    st.markdown("### Runtime boundary")
    st.code("UI: 127.0.0.1:8501\nOllama: 127.0.0.1:11434\nExternal AI API calls: none configured")
    st.caption("A localhost-only application is not by itself a certified air gap. For production, enforce outbound network restrictions with Windows Defender Firewall / network controls and independently monitor egress.")
