import io
import os
import time
import zipfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from pipeline.backends import ComfyUIBackend, OpenAIBackend
from pipeline.runner import run_pipeline
from pipeline.video import ffmpeg_available

load_dotenv()
st.set_page_config(page_title="Story to Video", page_icon="🎬", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1150px; padding-top: 2rem;}
.hero {padding: 2.2rem 2.4rem; border-radius: 18px; color: #fff; margin-bottom: 1.5rem;
       background: linear-gradient(120deg, #4a1d96 0%, #c026d3 50%, #fb923c 100%);
       box-shadow: 0 6px 20px rgba(74, 29, 150, .28);}
.hero h1 {color: #ffffff; margin: 0 0 .3rem 0; font-size: 2.3rem;}
.hero p {color: #f6e8ff; margin: 0 0 1rem 0; font-size: 1.05rem; max-width: 65%;}
.chip {display: inline-block; padding: .25rem .8rem; margin: 0 .4rem .3rem 0; border-radius: 999px;
       background: rgba(255,255,255,.2); font-size: .85rem;}
.stButton > button {height: 3rem; font-weight: 600; border-radius: 10px;
       background: linear-gradient(120deg, #c026d3, #fb923c); color: #ffffff; border: none;}
.stButton > button:hover {background: linear-gradient(120deg, #a21caf, #f97316); color: #ffffff;}
</style>
<div class="hero">
  <h1>🎬 Story to Video</h1>
  <p>Drop an idea. AI plans the scenes, characters and style, then makes a narrated illustrated video.</p>
</div>
""", unsafe_allow_html=True)

EXAMPLE = ("Two children, Ife and Chidi, spend a sunny Saturday at a community playground in Lagos, "
           "learning to share, take turns and stay safe while they play.")

story = st.text_area("💡 Your story, description or idea", EXAMPLE, height=160,
                     help="Anything works: a one-line idea or a full story. AI decides the scenes (up to 8), characters and visual style.")
# engine = st.radio("Image engine", ["OpenAI", "ComfyUI (local)"], horizontal=True)
engine = 'OpenAI'
if engine.startswith("ComfyUI"):
    with st.expander("ComfyUI settings", expanded=True):
        c1, c2 = st.columns(2)
        url = c1.text_input("Server URL", os.getenv("COMFYUI_URL", "http://127.0.0.1:8188"))
        ckpt = c2.text_input("Checkpoint", os.getenv("COMFYUI_CHECKPOINT", "sd_xl_base_1.0.safetensors"))

if st.button("✨ Generate video", type="primary", use_container_width=True):
    api_key = os.getenv("OPENAI_API_KEY")
    if not story.strip():
        st.warning("Please enter a story or idea first.")
    elif not api_key:
        st.error("OPENAI_API_KEY not found. Add it to your .env file (needed for planning and narration).")
    elif not ffmpeg_available():
        st.error("FFmpeg was not found on this machine. Install it and make sure it is on your PATH.")
    else:
        started = time.time()
        try:
            backend = OpenAIBackend(api_key) if engine == "OpenAI" else ComfyUIBackend(url, ckpt)
            out_dir = Path("outputs") / time.strftime("%Y%m%d_%H%M%S")
            weights = {"planning": (0.0, 0.1, "Planning the storyboard"),
                       "images": (0.1, 0.55, "Generating scene images"),
                       "narration": (0.65, 0.2, "Recording narration"),
                       "video": (0.85, 0.15, "Assembling video")}
            with st.status("Building your video...", expanded=True) as status:
                bar = st.progress(0.0, text="Planning the storyboard...")

                def on_progress(stage, done, total):
                    start, span, label = weights[stage]
                    bar.progress(min(start + span * done / total, 1.0), text=f"{label} ({done}/{total})")

                result = run_pipeline(story, backend, out_dir, api_key=api_key, on_progress=on_progress)
                status.update(label="Done", state="complete", expanded=False)
            result["seconds"] = time.time() - started
            st.session_state["out"] = result
        except Exception as e:
            st.error(f"Generation failed: {e}")

out = st.session_state.get("out")
if out:
    plan = out["plan"]
    st.divider()
    st.subheader(plan["title"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Scenes", len(out["scenes"]))
    m2.metric("Generated in", f"{out['seconds']:.0f}s")
    m3.metric("Format", "320*240 · MP4")

    with st.expander("🧠 AI storyboard plan (style and characters)"):
        st.markdown(f"**Visual style:** {plan['style']}")
        for name, desc in plan["characters"].items():
            st.markdown(f"- **{name}:** {desc}")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for f in Path(out["dir"]).iterdir():
            z.write(f, f.name)

    tab_video, tab_scenes = st.tabs(["🎬 Video", "🖼️ Scenes"])
    with tab_video:
        st.video(out["video"])
        d1, d2 = st.columns(2)
        d1.download_button("⬇️ Download video (MP4)", Path(out["video"]).read_bytes(),
                           "story_video.mp4", "video/mp4", use_container_width=True)
        d2.download_button("📦 Download everything (ZIP)", buf.getvalue(),
                           "story_package.zip", "application/zip", use_container_width=True)
    with tab_scenes:
        cols = st.columns(2, gap="large")
        for i, s in enumerate(out["scenes"]):
            with cols[i % 2].container(border=True):
                st.markdown(f"**Scene {s['index']}**")
                st.image(s["image"], use_container_width=True)
                st.caption(s["text"])
                st.audio(s["audio"])
                with st.expander("Prompt used"):
                    st.code(s["prompt"], language=None)
