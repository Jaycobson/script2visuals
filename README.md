# Story to Video

Drop a story or idea. An OpenAI model plans the storyboard (up to 8 scenes, narration, characters, visual style), then the app generates consistent images, Nigerian-English narration and an FFmpeg video.

**Pipeline:** story -> AI planner (`pipeline/planner.py`) -> character-consistent prompts -> images (OpenAI or local ComfyUI) -> narration -> video.

## Run
```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env, then add OPENAI_API_KEY
streamlit run app.py
```
Requires FFmpeg (and ffprobe) on your PATH. Tests: `pytest`.

## Notes
- Fixed settings: 1024x1024, low quality, narration and video always on.
- The planner tries `OPENAI_PLANNER_MODEL` (optional in `.env`), then `gpt-5.6`, `gpt-4.1`, `gpt-4o-mini`.
- Scene 1 is the visual reference for the others, which then run in parallel.
- Each run saves images, audio, video and `plan.json` in `outputs/`.
