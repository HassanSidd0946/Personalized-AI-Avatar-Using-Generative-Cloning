# # """
# # app.py - FastAPI Backend for AI Avatar Pipeline
# # Location : MODAL/app.py

# # IMPORTANT: Variable named `fastapi_app` to avoid clash with
# # Modal's `app` object that gets imported via main_pipeline.py

# # Run:
# #   pip install supabase
# #   uvicorn app:fastapi_app --reload --port 8000

# # Required environment variables (add to MODAL/.env):
# #   SUPABASE_URL = https://xxxx.supabase.co
# #   SUPABASE_KEY = your-anon-or-service-role-key

# # Endpoints:
# #   GET  /health                - liveness check
# #   POST /generate              - JSON body with direct text
# #   POST /generate-from-file    - multipart .txt file upload
# #   GET  /video/{filename}      - download local video (fallback)
# # """

# # import os
# # from pathlib import Path

# # from fastapi import FastAPI, File, Form, HTTPException, UploadFile
# # from fastapi.middleware.cors import CORSMiddleware
# # from fastapi.responses import FileResponse
# # from pydantic import BaseModel, field_validator
# # from supabase import Client, create_client

# # from text_cleaner import CleanResult, clean_text

# # # ---------------------------------------------------------------------------
# # # Lazy import — prevents Modal's app object from crashing uvicorn startup
# # # ---------------------------------------------------------------------------
# # _run_pipeline = None

# # def _get_pipeline():
# #     global _run_pipeline
# #     if _run_pipeline is None:
# #         from main_pipeline import run_pipeline
# #         _run_pipeline = run_pipeline
# #     return _run_pipeline


# # # ---------------------------------------------------------------------------
# # # Supabase client — initialized once at startup from environment variables
# # #
# # # Add these to your MODAL/.env file:
# # #   SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
# # #   SUPABASE_KEY=your-anon-or-service-role-key
# # #
# # # Storage bucket : avatars       (create in Supabase dashboard -> Storage)
# # # Database table : generations   (SQL to create is at the bottom of this file)
# # # ---------------------------------------------------------------------------
# # # Load .env file explicitly so keys are available before supabase init
# # try:
# #     from dotenv import load_dotenv
# #     load_dotenv()
# # except ImportError:
# #     pass  # python-dotenv optional — keys may come from system env

# # _raw_url: str = os.environ.get("SUPABASE_URL", "")
# # SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

# # # Sanitize URL — remove accidental trailing paths like /rest/v1/
# # # Supabase client needs only the base URL: https://xxxx.supabase.co
# # SUPABASE_URL: str = _raw_url.split("/rest/")[0].split("/auth/")[0].rstrip("/")

# # if not SUPABASE_URL or not SUPABASE_KEY:
# #     print(
# #         "\n[supabase] WARNING: SUPABASE_URL or SUPABASE_KEY not set.\n"
# #         "  Add them to your MODAL/.env file.\n"
# #         "  Upload/DB features will be disabled until they are set.\n"
# #     )
# #     supabase: Client | None = None
# # else:
# #     try:
# #         supabase: Client | None = create_client(SUPABASE_URL, SUPABASE_KEY)
# #         print(f"[supabase] Connected to: {SUPABASE_URL}")
# #     except Exception as e:
# #         print(f"[supabase] Init failed: {e}")
# #         supabase = None


# # # ---------------------------------------------------------------------------
# # # FastAPI app
# # # ---------------------------------------------------------------------------
# # fastapi_app = FastAPI(
# #     title="AI Avatar Pipeline API",
# #     description="Generate lip-synced AI avatar videos using XTTS-v2 + Wav2Lip",
# #     version="2.0.0",
# # )

# # # ---------------------------------------------------------------------------
# # # CORS — allows frontend (React/Next.js) on any origin to call this API
# # # Restrict allow_origins to specific domains in production
# # # ---------------------------------------------------------------------------
# # fastapi_app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["*"],       # e.g. ["https://yourdomain.com"] in production
# #     allow_credentials=True,
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )


# # # ---------------------------------------------------------------------------
# # # Schemas
# # # ---------------------------------------------------------------------------

# # class GenerateRequest(BaseModel):
# #     text: str
# #     user_id: str = "anonymous"               # Firebase UID from frontend
# #     ref_audio: str = "XTTS-v2/ref_audio.wav"
# #     face: str = "WavTOlip/avatar1.jpg"
# #     output_dir: str = "output"
# #     voice_file: str | None = None
# #     use_deployed: bool = False

# #     @field_validator("text")
# #     @classmethod
# #     def text_must_not_be_empty(cls, v: str) -> str:
# #         if not v or not v.strip():
# #             raise ValueError("text field must not be empty")
# #         return v

# #     @field_validator("voice_file", mode="before")
# #     @classmethod
# #     def sanitize_voice_file(cls, v):
# #         # Swagger UI sends literal "string" as placeholder — treat as None
# #         if v is None or str(v).strip().lower() in ("string", "", "null", "none"):
# #             return None
# #         return v


# # class GenerateResponse(BaseModel):
# #     status: str
# #     video_url: str           # Supabase public URL (or local path as fallback)
# #     stored_in_cloud: bool    # True = uploaded to Supabase, False = local only
# #     user_id: str
# #     original_text: str
# #     cleaned_text: str
# #     cleaning_applied: bool
# #     cleaning_steps: list[str]
# #     char_delta: int


# # # ---------------------------------------------------------------------------
# # # Supabase helpers
# # # ---------------------------------------------------------------------------

# # def _upload_to_supabase(local_video_path: str, user_id: str) -> str | None:
# #     """
# #     Upload local .mp4 to Supabase Storage bucket 'avatars'.

# #     Storage path format:  {user_id}/{filename}
# #     Example:              uid_abc123/avatar_20260601_090346.mp4

# #     Returns the public URL string, or None if upload fails.
# #     """
# #     if supabase is None:
# #         print("[supabase] Client not initialized — skipping upload.")
# #         return None

# #     filename = Path(local_video_path).name
# #     storage_path = f"{user_id}/{filename}"

# #     try:
# #         with open(local_video_path, "rb") as f:
# #             video_bytes = f.read()

# #         print(f"[supabase] Uploading {len(video_bytes)/1024/1024:.2f} MB -> avatars/{storage_path}")

# #         supabase.storage.from_("avatars").upload(
# #             path=storage_path,
# #             file=video_bytes,
# #             file_options={"content-type": "video/mp4"},
# #         )

# #         public_url: str = supabase.storage.from_("avatars").get_public_url(storage_path)
# #         print(f"[supabase] Upload successful: {public_url}")
# #         return public_url

# #     except Exception as e:
# #         print(f"[supabase] Upload failed: {e}")
# #         return None


# # def _insert_generation_record(
# #     user_id: str,
# #     cleaned_text: str,
# #     video_url: str,
# # ) -> None:
# #     """
# #     Insert a row into the 'generations' table.

# #     Table schema (run this SQL in Supabase SQL Editor):
# #     -------------------------------------------------------
# #     create table generations (
# #         id          uuid primary key default gen_random_uuid(),
# #         user_id     text not null,
# #         text_used   text not null,
# #         video_url   text not null,
# #         created_at  timestamptz default now()
# #     );
# #     -------------------------------------------------------
# #     """
# #     if supabase is None:
# #         print("[supabase] Client not initialized — skipping DB insert.")
# #         return

# #     try:
# #         record = {
# #             "user_id":   user_id,
# #             "text_used": cleaned_text,
# #             "video_url": video_url,
# #         }
# #         supabase.table("generations").insert(record).execute()
# #         print(f"[supabase] DB record inserted for user: {user_id}")

# #     except Exception as e:
# #         # Non-fatal — video is already uploaded, just log the DB failure
# #         print(f"[supabase] DB insert failed (non-fatal): {e}")


# # def _cleanup_local_files(*paths: str) -> None:
# #     """Delete local files after cloud upload. Logs but never raises."""
# #     for path in paths:
# #         try:
# #             if path and Path(path).exists():
# #                 os.remove(path)
# #                 print(f"[cleanup] Deleted local file: {path}")
# #         except Exception as e:
# #             print(f"[cleanup] Could not delete {path}: {e}")


# # # ---------------------------------------------------------------------------
# # # Core pipeline runner — used by both endpoints
# # # ---------------------------------------------------------------------------

# # def _run(
# #     raw_text: str,
# #     user_id: str,
# #     ref_audio: str,
# #     face: str,
# #     output_dir: str,
# #     voice_file: str | None,
# #     use_deployed: bool,
# #     text_source: str,
# # ) -> GenerateResponse:

# #     # ── Step 1: Clean text ───────────────────────────────────────────────────
# #     result: CleanResult = clean_text(raw_text)

# #     print(f"\n[cleaner] Source   : {text_source}")
# #     print(f"[cleaner] Original : {result.original[:100]}")
# #     print(f"[cleaner] Cleaned  : {result.cleaned[:100]}")
# #     print(result.summary())

# #     if not result.cleaned:
# #         raise HTTPException(
# #             status_code=422,
# #             detail="Text is empty after cleaning. Input may contain only emojis or special characters."
# #         )

# #     # ── Step 2: Validate input file paths ────────────────────────────────────
# #     for label, path in [("ref_audio", ref_audio), ("face", face)]:
# #         if not Path(path).exists():
# #             raise HTTPException(
# #                 status_code=404,
# #                 detail=f"{label} not found: '{path}'"
# #             )

# #     # ── Step 3: Run pipeline — track generated files for cleanup ─────────────
# #     local_video_path: str | None = None
# #     local_voice_path: str | None = None

# #     try:
# #         local_video_path = _get_pipeline()(
# #             text=result.cleaned,
# #             ref_audio_path=ref_audio,
# #             face_path=face,
# #             output_dir=output_dir,
# #             voice_filename=voice_file,
# #             use_deployed=use_deployed,
# #         )

# #         # Derive voice path from video path (same timestamp, same output_dir)
# #         # main_pipeline saves voice as voice_<timestamp>.wav alongside the video
# #         video_stem = Path(local_video_path).stem          # avatar_20260601_090346
# #         timestamp = video_stem.replace("avatar_", "")     # 20260601_090346
# #         local_voice_path = str(Path(output_dir) / f"voice_{timestamp}.wav")

# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

# #     # ── Step 4: Upload to Supabase Storage ───────────────────────────────────
# #     stored_in_cloud = False
# #     video_url = local_video_path  # fallback to local path if upload fails

# #     try:
# #         public_url = _upload_to_supabase(local_video_path, user_id)

# #         if public_url:
# #             video_url = public_url
# #             stored_in_cloud = True

# #             # ── Step 5: Insert DB record ─────────────────────────────────────
# #             _insert_generation_record(
# #                 user_id=user_id,
# #                 cleaned_text=result.cleaned,
# #                 video_url=video_url,
# #             )

# #     finally:
# #         # ── Step 6: Cleanup local files ──────────────────────────────────────
# #         # Always runs — even if upload or DB insert raised an exception.
# #         # Only delete video locally if it was successfully uploaded to cloud.
# #         if stored_in_cloud:
# #             _cleanup_local_files(local_video_path, local_voice_path)
# #         else:
# #             # Keep local video as fallback — don't delete if cloud failed
# #             print(f"[cleanup] Keeping local video (cloud upload failed): {local_video_path}")
# #             if local_voice_path:
# #                 _cleanup_local_files(local_voice_path)  # voice always deletable

# #     return GenerateResponse(
# #         status="success",
# #         video_url=video_url,
# #         stored_in_cloud=stored_in_cloud,
# #         user_id=user_id,
# #         original_text=result.original,
# #         cleaned_text=result.cleaned,
# #         cleaning_applied=result.was_modified,
# #         cleaning_steps=result.steps,
# #         char_delta=result.char_delta,
# #     )


# # # ---------------------------------------------------------------------------
# # # Endpoints
# # # ---------------------------------------------------------------------------

# # @fastapi_app.get("/health")
# # def health_check():
# #     return {
# #         "status": "ok",
# #         "service": "AI Avatar Pipeline API",
# #         "supabase_connected": supabase is not None,
# #     }


# # @fastapi_app.post("/generate", response_model=GenerateResponse)
# # def generate_from_text(request: GenerateRequest):
# #     """
# #     Generate avatar video from a direct text string.

# #     Request body (JSON):
# #         {
# #             "text": "Hello, I am your AI avatar.",
# #             "user_id": "firebase_uid_abc123",
# #             "ref_audio": "XTTS-v2/ref_audio.wav",
# #             "face": "WavTOlip/avatar1.jpg"
# #         }
# #     """
# #     return _run(
# #         raw_text=request.text,
# #         user_id=request.user_id,
# #         ref_audio=request.ref_audio,
# #         face=request.face,
# #         output_dir=request.output_dir,
# #         voice_file=request.voice_file,
# #         use_deployed=request.use_deployed,
# #         text_source="direct JSON",
# #     )


# # @fastapi_app.post("/generate-from-file", response_model=GenerateResponse)
# # async def generate_from_file(
# #     file: UploadFile = File(..., description=".txt file containing the avatar script"),
# #     user_id: str = Form(default="anonymous"),
# #     ref_audio: str = Form(default="XTTS-v2/ref_audio.wav"),
# #     face: str = Form(default="WavTOlip/avatar1.jpg"),
# #     output_dir: str = Form(default="output"),
# #     voice_file: str | None = Form(default=None),
# #     use_deployed: bool = Form(default=False),
# # ):
# #     """Generate avatar video from an uploaded .txt file."""

# #     if not file.filename:
# #         raise HTTPException(status_code=400, detail="No file provided.")

# #     if not file.filename.lower().endswith(".txt"):
# #         raise HTTPException(
# #             status_code=400,
# #             detail=f"Only .txt files accepted. Got: '{file.filename}'"
# #         )

# #     try:
# #         raw_bytes = await file.read()
# #         raw_text = raw_bytes.decode("utf-8")
# #     except UnicodeDecodeError:
# #         raise HTTPException(
# #             status_code=400,
# #             detail="File encoding error. Please save your .txt file as UTF-8."
# #         )

# #     if not raw_text.strip():
# #         raise HTTPException(status_code=400, detail="Uploaded file is empty.")

# #     print(f"\n[upload] File    : {file.filename}")
# #     print(f"[upload] Size    : {len(raw_bytes)} bytes")
# #     print(f"[upload] Lines   : {raw_text.count(chr(10)) + 1}")
# #     print(f"[upload] user_id : {user_id}")

# #     return _run(
# #         raw_text=raw_text,
# #         user_id=user_id,
# #         ref_audio=ref_audio,
# #         face=face,
# #         output_dir=output_dir,
# #         voice_file=voice_file,
# #         use_deployed=use_deployed,
# #         text_source=f"uploaded file: {file.filename}",
# #     )


# # @fastapi_app.get("/video/{filename}")
# # def download_video(filename: str):
# #     """Download a locally stored video by filename (fallback if Supabase is not configured)."""
# #     safe_name = Path(filename).name
# #     video_path = Path("output") / safe_name

# #     if not video_path.exists():
# #         raise HTTPException(
# #             status_code=404,
# #             detail=f"Video not found locally: '{safe_name}'. It may have been uploaded to Supabase cloud."
# #         )

# #     return FileResponse(
# #         path=str(video_path),
# #         media_type="video/mp4",
# #         filename=safe_name,
# #     )


# # @fastapi_app.get("/history/{user_id}")
# # def get_user_history(user_id: str, limit: int = 10):
# #     """
# #     Fetch generation history for a user from Supabase DB.

# #     Returns last `limit` generations (default 10), newest first.
# #     """
# #     if supabase is None:
# #         raise HTTPException(
# #             status_code=503,
# #             detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY in .env"
# #         )

# #     try:
# #         response = (
# #             supabase.table("generations")
# #             .select("id, user_id, text_used, video_url, created_at")
# #             .eq("user_id", user_id)
# #             .order("created_at", desc=True)
# #             .limit(limit)
# #             .execute()
# #         )
# #         return {"status": "ok", "user_id": user_id, "records": response.data}

# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"DB query failed: {str(e)}")


























# """
# app.py - FastAPI Backend for AI Avatar Pipeline
# Location : MODAL/app.py

# IMPORTANT: Variable named `fastapi_app` to avoid clash with
# Modal's `app` object that gets imported via main_pipeline.py

# Run:
#   pip install supabase
#   uvicorn app:fastapi_app --reload --port 8000

# Required environment variables (add to MODAL/.env):
#   SUPABASE_URL = https://xxxx.supabase.co
#   SUPABASE_KEY = your-anon-or-service-role-key

# Endpoints:
#   GET  /health                - liveness check
#   POST /generate              - JSON body with direct text
#   POST /generate-from-file    - multipart .txt file upload
#   GET  /video/{filename}      - download local video (fallback)
# """

# import os
# from pathlib import Path

# from fastapi import FastAPI, File, Form, HTTPException, UploadFile
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import FileResponse
# from pydantic import BaseModel, field_validator
# from supabase import Client, create_client

# from text_cleaner import CleanResult, clean_text

# # ---------------------------------------------------------------------------
# # Lazy import — prevents Modal's app object from crashing uvicorn startup
# # ---------------------------------------------------------------------------
# _run_pipeline = None

# def _get_pipeline():
#     global _run_pipeline
#     if _run_pipeline is None:
#         from main_pipeline import run_pipeline
#         _run_pipeline = run_pipeline
#     return _run_pipeline


# # ---------------------------------------------------------------------------
# # Supabase client — initialized once at startup from environment variables
# #
# # Add these to your MODAL/.env file:
# #   SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
# #   SUPABASE_KEY=your-anon-or-service-role-key
# #
# # Storage bucket : avatars       (create in Supabase dashboard -> Storage)
# # Database table : generations   (SQL to create is at the bottom of this file)
# # ---------------------------------------------------------------------------
# # Load .env file explicitly so keys are available before supabase init
# try:
#     from dotenv import load_dotenv
#     load_dotenv()
# except ImportError:
#     pass  # python-dotenv optional — keys may come from system env

# _raw_url: str = os.environ.get("SUPABASE_URL", "")
# SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

# # Sanitize URL — remove accidental trailing paths like /rest/v1/
# # Supabase client needs only the base URL: https://xxxx.supabase.co
# SUPABASE_URL: str = _raw_url.split("/rest/")[0].split("/auth/")[0].rstrip("/")

# if not SUPABASE_URL or not SUPABASE_KEY:
#     print(
#         "\n[supabase] WARNING: SUPABASE_URL or SUPABASE_KEY not set.\n"
#         "  Add them to your MODAL/.env file.\n"
#         "  Upload/DB features will be disabled until they are set.\n"
#     )
#     supabase: Client | None = None
# else:
#     try:
#         supabase: Client | None = create_client(SUPABASE_URL, SUPABASE_KEY)
#         print(f"[supabase] Connected to: {SUPABASE_URL}")
#     except Exception as e:
#         print(f"[supabase] Init failed: {e}")
#         supabase = None


# # ---------------------------------------------------------------------------
# # FastAPI app
# # ---------------------------------------------------------------------------
# fastapi_app = FastAPI(
#     title="AI Avatar Pipeline API",
#     description="Generate lip-synced AI avatar videos using XTTS-v2 + Wav2Lip",
#     version="2.0.0",
# )

# # ---------------------------------------------------------------------------
# # CORS — allows frontend (React/Next.js) on any origin to call this API
# # Restrict allow_origins to specific domains in production
# # ---------------------------------------------------------------------------
# fastapi_app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],       # e.g. ["https://yourdomain.com"] in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # ---------------------------------------------------------------------------
# # Schemas
# # ---------------------------------------------------------------------------

# class GenerateRequest(BaseModel):
#     text: str
#     user_id: str = "anonymous"               # Firebase UID from frontend
#     ref_audio: str = "XTTS-v2/ref_audio.wav"
#     face: str = "WavTOlip/avatar1.jpg"
#     output_dir: str = "output"
#     voice_file: str | None = None
#     use_deployed: bool = False

#     @field_validator("text")
#     @classmethod
#     def text_must_not_be_empty(cls, v: str) -> str:
#         if not v or not v.strip():
#             raise ValueError("text field must not be empty")
#         return v

#     @field_validator("voice_file", mode="before")
#     @classmethod
#     def sanitize_voice_file(cls, v):
#         # Swagger UI sends literal "string" as placeholder — treat as None
#         if v is None or str(v).strip().lower() in ("string", "", "null", "none"):
#             return None
#         return v


# class GenerateResponse(BaseModel):
#     status: str
#     video_url: str           # Supabase public URL (or local path as fallback)
#     stored_in_cloud: bool    # True = uploaded to Supabase, False = local only
#     user_id: str
#     original_text: str
#     cleaned_text: str
#     cleaning_applied: bool
#     cleaning_steps: list[str]
#     char_delta: int


# # ---------------------------------------------------------------------------
# # Supabase helpers
# # ---------------------------------------------------------------------------

# def _upload_to_supabase(local_video_path: str, user_id: str) -> str | None:
#     """
#     Upload local .mp4 to Supabase Storage bucket 'avatars'.

#     Storage path format:  {user_id}/{filename}
#     Example:              uid_abc123/avatar_20260601_090346.mp4

#     Returns the public URL string, or None if upload fails.
#     """
#     if supabase is None:
#         print("[supabase] Client not initialized — skipping upload.")
#         return None

#     filename = Path(local_video_path).name
#     storage_path = f"{user_id}/{filename}"

#     try:
#         with open(local_video_path, "rb") as f:
#             video_bytes = f.read()

#         print(f"[supabase] Uploading {len(video_bytes)/1024/1024:.2f} MB -> avatars/{storage_path}")

#         supabase.storage.from_("avatars").upload(
#             path=storage_path,
#             file=video_bytes,
#             file_options={"content-type": "video/mp4"},
#         )

#         public_url: str = supabase.storage.from_("avatars").get_public_url(storage_path)
#         print(f"[supabase] Upload successful: {public_url}")
#         return public_url

#     except Exception as e:
#         print(f"[supabase] Upload failed: {e}")
#         return None


# def _insert_generation_record(
#     user_id: str,
#     cleaned_text: str,
#     video_url: str,
# ) -> None:
#     """
#     Insert a row into the 'generations' table.

#     Table schema (run this SQL in Supabase SQL Editor):
#     -------------------------------------------------------
#     create table generations (
#         id          uuid primary key default gen_random_uuid(),
#         user_id     text not null,
#         text_used   text not null,
#         video_url   text not null,
#         created_at  timestamptz default now()
#     );
#     -------------------------------------------------------
#     """
#     if supabase is None:
#         print("[supabase] Client not initialized — skipping DB insert.")
#         return

#     try:
#         record = {
#             "user_id":   user_id,
#             "text_used": cleaned_text,
#             "video_url": video_url,
#         }
#         supabase.table("generations").insert(record).execute()
#         print(f"[supabase] DB record inserted for user: {user_id}")

#     except Exception as e:
#         # Non-fatal — video is already uploaded, just log the DB failure
#         print(f"[supabase] DB insert failed (non-fatal): {e}")


# def _cleanup_local_files(*paths: str) -> None:
#     """Delete local files after cloud upload. Logs but never raises."""
#     for path in paths:
#         try:
#             if path and Path(path).exists():
#                 os.remove(path)
#                 print(f"[cleanup] Deleted local file: {path}")
#         except Exception as e:
#             print(f"[cleanup] Could not delete {path}: {e}")


# # ---------------------------------------------------------------------------
# # Upload helper — saves UploadFile to disk, returns local path
# # ---------------------------------------------------------------------------

# async def _save_upload_to_disk(upload_file: UploadFile, out_dir: str) -> str:
#     """
#     Read an UploadFile and save it under out_dir/user_upload_<filename>.
#     Returns the saved local path string.

#     The 'user_upload_' prefix makes temp files easy to identify for cleanup.
#     """
#     Path(out_dir).mkdir(parents=True, exist_ok=True)

#     # Sanitize filename — strip path components from browser-supplied names
#     safe_filename = f"user_upload_{Path(upload_file.filename).name}"
#     dest_path = str(Path(out_dir) / safe_filename)

#     file_bytes = await upload_file.read()
#     with open(dest_path, "wb") as f:
#         f.write(file_bytes)

#     print(f"[upload] Saved temp file: {dest_path}  ({len(file_bytes)/1024:.1f} KB)")
#     return dest_path


# # ---------------------------------------------------------------------------
# # Core pipeline runner — used by both endpoints
# # ---------------------------------------------------------------------------

# def _run(
#     raw_text: str,
#     user_id: str,
#     ref_audio: str,       # local path — either pre-saved temp file or static path
#     face: str,            # local path — either pre-saved temp file or static path
#     output_dir: str,
#     voice_file: str | None,
#     use_deployed: bool,
#     text_source: str,
#     temp_files: list[str] | None = None,  # extra temp paths to always delete
# ) -> GenerateResponse:

#     # ── Step 1: Clean text ───────────────────────────────────────────────────
#     result: CleanResult = clean_text(raw_text)

#     print(f"\n[cleaner] Source   : {text_source}")
#     print(f"[cleaner] Original : {result.original[:100]}")
#     print(f"[cleaner] Cleaned  : {result.cleaned[:100]}")
#     print(result.summary())

#     if not result.cleaned:
#         raise HTTPException(
#             status_code=422,
#             detail="Text is empty after cleaning. Input may contain only emojis or special characters."
#         )

#     # ── Step 2: Validate input file paths ────────────────────────────────────
#     for label, path in [("ref_audio", ref_audio), ("face", face)]:
#         if not Path(path).exists():
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"{label} not found: '{path}'"
#             )

#     # ── Step 3: Run pipeline — track generated files for cleanup ─────────────
#     local_video_path: str | None = None
#     local_voice_path: str | None = None

#     try:
#         local_video_path = _get_pipeline()(
#             text=result.cleaned,
#             ref_audio_path=ref_audio,
#             face_path=face,
#             output_dir=output_dir,
#             voice_filename=voice_file,
#             use_deployed=use_deployed,
#         )

#         # Derive voice path from video path (same timestamp, same output_dir)
#         # main_pipeline saves voice as voice_<timestamp>.wav alongside the video
#         video_stem = Path(local_video_path).stem          # avatar_20260601_090346
#         timestamp = video_stem.replace("avatar_", "")     # 20260601_090346
#         local_voice_path = str(Path(output_dir) / f"voice_{timestamp}.wav")

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

#     # ── Step 4: Upload to Supabase Storage ───────────────────────────────────
#     stored_in_cloud = False
#     video_url = local_video_path  # fallback to local path if upload fails

#     try:
#         public_url = _upload_to_supabase(local_video_path, user_id)

#         if public_url:
#             video_url = public_url
#             stored_in_cloud = True

#             # ── Step 5: Insert DB record ─────────────────────────────────────
#             _insert_generation_record(
#                 user_id=user_id,
#                 cleaned_text=result.cleaned,
#                 video_url=video_url,
#             )

#     finally:
#         # ── Step 6: Cleanup local files ──────────────────────────────────────
#         # Always runs — even if upload or DB insert raised an exception.
#         # temp_files (uploaded face + audio) are ALWAYS deleted regardless of outcome.
#         # Only delete generated video locally if it was successfully uploaded to cloud.
#         if temp_files:
#             _cleanup_local_files(*temp_files)   # user uploads — always delete

#         if stored_in_cloud:
#             _cleanup_local_files(local_video_path, local_voice_path)
#         else:
#             # Keep local video as fallback — don't delete if cloud failed
#             print(f"[cleanup] Keeping local video (cloud upload failed): {local_video_path}")
#             if local_voice_path:
#                 _cleanup_local_files(local_voice_path)  # voice always deletable

#     return GenerateResponse(
#         status="success",
#         video_url=video_url,
#         stored_in_cloud=stored_in_cloud,
#         user_id=user_id,
#         original_text=result.original,
#         cleaned_text=result.cleaned,
#         cleaning_applied=result.was_modified,
#         cleaning_steps=result.steps,
#         char_delta=result.char_delta,
#     )


# # ---------------------------------------------------------------------------
# # Endpoints
# # ---------------------------------------------------------------------------

# @fastapi_app.get("/health")
# def health_check():
#     return {
#         "status": "ok",
#         "service": "AI Avatar Pipeline API",
#         "supabase_connected": supabase is not None,
#     }


# @fastapi_app.post("/generate", response_model=GenerateResponse)
# async def generate_from_text(
#     text: str = Form(..., description="Avatar script text"),
#     user_id: str = Form(default="anonymous", description="Firebase UID from frontend"),
#     face_file: UploadFile = File(..., description="Avatar face image (.jpg/.png)"),
#     ref_audio_file: UploadFile = File(..., description="Reference voice audio (.wav/.mp3)"),
#     output_dir: str = Form(default="output"),
#     use_deployed: bool = Form(default=False),
# ):
#     """
#     Generate avatar video from a direct text string + uploaded face + audio.

#     multipart/form-data fields:
#       text           — avatar script (required)
#       user_id        — Firebase UID (optional, default: anonymous)
#       face_file      — face image upload (.jpg / .png)
#       ref_audio_file — voice reference upload (.wav / .mp3)
#       output_dir     — output directory (optional)
#       use_deployed   — use deployed Modal app (optional)
#     """
#     # Save uploaded files to disk first — _run() needs local paths
#     temp_face_path  = await _save_upload_to_disk(face_file,      output_dir)
#     temp_audio_path = await _save_upload_to_disk(ref_audio_file, output_dir)

#     return _run(
#         raw_text=text,
#         user_id=user_id,
#         ref_audio=temp_audio_path,
#         face=temp_face_path,
#         output_dir=output_dir,
#         voice_file=None,
#         use_deployed=use_deployed,
#         text_source="direct form text",
#         temp_files=[temp_face_path, temp_audio_path],
#     )


# @fastapi_app.post("/generate-from-file", response_model=GenerateResponse)
# async def generate_from_file(
#     script_file: UploadFile = File(..., description=".txt file containing the avatar script"),
#     face_file: UploadFile = File(..., description="Avatar face image (.jpg/.png)"),
#     ref_audio_file: UploadFile = File(..., description="Reference voice audio (.wav/.mp3)"),
#     user_id: str = Form(default="anonymous"),
#     output_dir: str = Form(default="output"),
#     use_deployed: bool = Form(default=False),
# ):
#     """
#     Generate avatar video from an uploaded .txt script + face image + voice audio.

#     multipart/form-data fields:
#       script_file    — .txt file with avatar script (required)
#       face_file      — face image upload (.jpg / .png) (required)
#       ref_audio_file — voice reference upload (.wav / .mp3) (required)
#       user_id        — Firebase UID (optional)
#       output_dir     — output directory (optional)
#       use_deployed   — use deployed Modal app (optional)
#     """
#     # ── Validate and read the script .txt file ───────────────────────────────
#     if not script_file.filename:
#         raise HTTPException(status_code=400, detail="No script file provided.")

#     if not script_file.filename.lower().endswith(".txt"):
#         raise HTTPException(
#             status_code=400,
#             detail=f"Only .txt script files accepted. Got: '{script_file.filename}'"
#         )

#     try:
#         raw_bytes = await script_file.read()
#         raw_text = raw_bytes.decode("utf-8")
#     except UnicodeDecodeError:
#         raise HTTPException(
#             status_code=400,
#             detail="Script file encoding error. Please save your .txt file as UTF-8."
#         )

#     if not raw_text.strip():
#         raise HTTPException(status_code=400, detail="Script file is empty.")

#     print(f"\n[upload] Script  : {script_file.filename}")
#     print(f"[upload] Size    : {len(raw_bytes)} bytes")
#     print(f"[upload] Lines   : {raw_text.count(chr(10)) + 1}")
#     print(f"[upload] user_id : {user_id}")

#     # ── Save face + audio uploads to disk ────────────────────────────────────
#     temp_face_path  = await _save_upload_to_disk(face_file,      output_dir)
#     temp_audio_path = await _save_upload_to_disk(ref_audio_file, output_dir)

#     return _run(
#         raw_text=raw_text,
#         user_id=user_id,
#         ref_audio=temp_audio_path,
#         face=temp_face_path,
#         output_dir=output_dir,
#         voice_file=None,
#         use_deployed=use_deployed,
#         text_source=f"uploaded script: {script_file.filename}",
#         temp_files=[temp_face_path, temp_audio_path],
#     )


# @fastapi_app.get("/video/{filename}")
# def download_video(filename: str):
#     """Download a locally stored video by filename (fallback if Supabase is not configured)."""
#     safe_name = Path(filename).name
#     video_path = Path("output") / safe_name

#     if not video_path.exists():
#         raise HTTPException(
#             status_code=404,
#             detail=f"Video not found locally: '{safe_name}'. It may have been uploaded to Supabase cloud."
#         )

#     return FileResponse(
#         path=str(video_path),
#         media_type="video/mp4",
#         filename=safe_name,
#     )


# @fastapi_app.get("/history/{user_id}")
# def get_user_history(user_id: str, limit: int = 10):
#     """
#     Fetch generation history for a user from Supabase DB.

#     Returns last `limit` generations (default 10), newest first.
#     """
#     if supabase is None:
#         raise HTTPException(
#             status_code=503,
#             detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY in .env"
#         )

#     try:
#         response = (
#             supabase.table("generations")
#             .select("id, user_id, text_used, video_url, created_at")
#             .eq("user_id", user_id)
#             .order("created_at", desc=True)
#             .limit(limit)
#             .execute()
#         )
#         return {"status": "ok", "user_id": user_id, "records": response.data}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"DB query failed: {str(e)}")






































































"""
app.py - FastAPI Backend for AI Avatar Pipeline
Location : MODAL/app.py

IMPORTANT: Variable named `fastapi_app` to avoid clash with
Modal's `app` object that gets imported via main_pipeline.py

Run:
  pip install supabase
  uvicorn app:fastapi_app --reload --port 8000

Required environment variables (add to MODAL/.env):
  SUPABASE_URL = https://xxxx.supabase.co
  SUPABASE_KEY = your-anon-or-service-role-key

Endpoints:
  GET  /health                - liveness check
  POST /generate              - JSON body with direct text
  POST /generate-from-file    - multipart .txt file upload
  GET  /video/{filename}      - download local video (fallback)
"""

import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from supabase import Client, create_client

from LLM_Cleaner import llm_clean_text

# ---------------------------------------------------------------------------
# Lazy import — prevents Modal's app object from crashing uvicorn startup
# ---------------------------------------------------------------------------
_run_pipeline = None

def _get_pipeline():
    global _run_pipeline
    if _run_pipeline is None:
        from main_pipeline import run_pipeline
        _run_pipeline = run_pipeline
    return _run_pipeline


# ---------------------------------------------------------------------------
# Supabase client — initialized once at startup from environment variables
#
# Add these to your MODAL/.env file:
#   SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
#   SUPABASE_KEY=your-anon-or-service-role-key
#
# Storage bucket : avatars       (create in Supabase dashboard -> Storage)
# Database table : generations   (SQL to create is at the bottom of this file)
# ---------------------------------------------------------------------------
# Load .env file explicitly so keys are available before supabase init
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional — keys may come from system env

_raw_url: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

# Sanitize URL — remove accidental trailing paths like /rest/v1/
# Supabase client needs only the base URL: https://xxxx.supabase.co
SUPABASE_URL: str = _raw_url.split("/rest/")[0].split("/auth/")[0].rstrip("/")

if not SUPABASE_URL or not SUPABASE_KEY:
    print(
        "\n[supabase] WARNING: SUPABASE_URL or SUPABASE_KEY not set.\n"
        "  Add them to your MODAL/.env file.\n"
        "  Upload/DB features will be disabled until they are set.\n"
    )
    supabase: Client | None = None
else:
    try:
        supabase: Client | None = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"[supabase] Connected to: {SUPABASE_URL}")
    except Exception as e:
        print(f"[supabase] Init failed: {e}")
        supabase = None


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
fastapi_app = FastAPI(
    title="AI Avatar Pipeline API",
    description="Generate lip-synced AI avatar videos using XTTS-v2 + Wav2Lip",
    version="2.0.0",
)

# ---------------------------------------------------------------------------
# CORS — allows frontend (React/Next.js) on any origin to call this API
# Restrict allow_origins to specific domains in production
# ---------------------------------------------------------------------------
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # e.g. ["https://yourdomain.com"] in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    text: str
    user_id: str = "anonymous"               # Firebase UID from frontend
    ref_audio: str = "XTTS-v2/ref_audio.wav"
    face: str = "WavTOlip/avatar1.jpg"
    output_dir: str = "output"
    voice_file: str | None = None
    use_deployed: bool = False

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text field must not be empty")
        return v

    @field_validator("voice_file", mode="before")
    @classmethod
    def sanitize_voice_file(cls, v):
        # Swagger UI sends literal "string" as placeholder — treat as None
        if v is None or str(v).strip().lower() in ("string", "", "null", "none"):
            return None
        return v


class GenerateResponse(BaseModel):
    status: str
    video_url: str           # Supabase public URL (or local path as fallback)
    stored_in_cloud: bool    # True = uploaded to Supabase, False = local only
    user_id: str
    original_text: str
    cleaned_text: str
    cleaning_applied: bool
    cleaning_steps: list[str]
    char_delta: int


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def _upload_to_supabase(local_video_path: str, user_id: str) -> str | None:
    """
    Upload local .mp4 to Supabase Storage bucket 'avatars'.

    Storage path format:  {user_id}/{filename}
    Example:              uid_abc123/avatar_20260601_090346.mp4

    Returns the public URL string, or None if upload fails.
    """
    if supabase is None:
        print("[supabase] Client not initialized — skipping upload.")
        return None

    filename = Path(local_video_path).name
    storage_path = f"{user_id}/{filename}"

    try:
        with open(local_video_path, "rb") as f:
            video_bytes = f.read()

        print(f"[supabase] Uploading {len(video_bytes)/1024/1024:.2f} MB -> avatars/{storage_path}")

        supabase.storage.from_("avatars").upload(
            path=storage_path,
            file=video_bytes,
            file_options={"content-type": "video/mp4"},
        )

        public_url: str = supabase.storage.from_("avatars").get_public_url(storage_path)
        print(f"[supabase] Upload successful: {public_url}")
        return public_url

    except Exception as e:
        print(f"[supabase] Upload failed: {e}")
        return None


def _insert_generation_record(
    user_id: str,
    cleaned_text: str,
    video_url: str,
) -> None:
    """
    Insert a row into the 'generations' table.

    Table schema (run this SQL in Supabase SQL Editor):
    -------------------------------------------------------
    create table generations (
        id          uuid primary key default gen_random_uuid(),
        user_id     text not null,
        text_used   text not null,
        video_url   text not null,
        created_at  timestamptz default now()
    );
    -------------------------------------------------------
    """
    if supabase is None:
        print("[supabase] Client not initialized — skipping DB insert.")
        return

    try:
        record = {
            "user_id":   user_id,
            "text_used": cleaned_text,
            "video_url": video_url,
        }
        supabase.table("generations").insert(record).execute()
        print(f"[supabase] DB record inserted for user: {user_id}")

    except Exception as e:
        # Non-fatal — video is already uploaded, just log the DB failure
        print(f"[supabase] DB insert failed (non-fatal): {e}")


def _cleanup_local_files(*paths: str) -> None:
    """Delete local files after cloud upload. Logs but never raises."""
    for path in paths:
        try:
            if path and Path(path).exists():
                os.remove(path)
                print(f"[cleanup] Deleted local file: {path}")
        except Exception as e:
            print(f"[cleanup] Could not delete {path}: {e}")


# ---------------------------------------------------------------------------
# Upload helper — saves UploadFile to disk, returns local path
# ---------------------------------------------------------------------------

async def _save_upload_to_disk(upload_file: UploadFile, out_dir: str) -> str:
    """
    Read an UploadFile and save it under out_dir/user_upload_<filename>.
    Returns the saved local path string.

    The 'user_upload_' prefix makes temp files easy to identify for cleanup.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # Sanitize filename — strip path components from browser-supplied names
    safe_filename = f"user_upload_{Path(upload_file.filename).name}"
    dest_path = str(Path(out_dir) / safe_filename)

    file_bytes = await upload_file.read()
    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    print(f"[upload] Saved temp file: {dest_path}  ({len(file_bytes)/1024:.1f} KB)")
    return dest_path


# ---------------------------------------------------------------------------
# Core pipeline runner — used by both endpoints
# ---------------------------------------------------------------------------

def _run(
    raw_text: str,
    user_id: str,
    ref_audio: str,       # local path — either pre-saved temp file or static path
    face: str,            # local path — either pre-saved temp file or static path
    output_dir: str,
    voice_file: str | None,
    use_deployed: bool,
    text_source: str,
    temp_files: list[str] | None = None,  # extra temp paths to always delete
) -> GenerateResponse:

    # ── Step 1: Normalize text via Azure OpenAI LLM ────────────────────────────
    print(f"\n[llm_cleaner] Source   : {text_source}")
    print(f"[llm_cleaner] Raw input : {raw_text[:120]}")

    cleaned_text: str = llm_clean_text(raw_text)

    if not cleaned_text or not cleaned_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Text is empty after LLM normalization. Check your input."
        )

    # ── Step 2: Validate input file paths ────────────────────────────────────
    for label, path in [("ref_audio", ref_audio), ("face", face)]:
        if not Path(path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"{label} not found: '{path}'"
            )

    # ── Step 3: Run pipeline — track generated files for cleanup ─────────────
    local_video_path: str | None = None
    local_voice_path: str | None = None

    try:
        local_video_path = _get_pipeline()(
            text=cleaned_text,
            ref_audio_path=ref_audio,
            face_path=face,
            output_dir=output_dir,
            voice_filename=voice_file,
            use_deployed=use_deployed,
        )

        # Derive voice path from video path (same timestamp, same output_dir)
        # main_pipeline saves voice as voice_<timestamp>.wav alongside the video
        video_stem = Path(local_video_path).stem          # avatar_20260601_090346
        timestamp = video_stem.replace("avatar_", "")     # 20260601_090346
        local_voice_path = str(Path(output_dir) / f"voice_{timestamp}.wav")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    # ── Step 4: Upload to Supabase Storage ───────────────────────────────────
    stored_in_cloud = False
    video_url = local_video_path  # fallback to local path if upload fails

    try:
        public_url = _upload_to_supabase(local_video_path, user_id)

        if public_url:
            video_url = public_url
            stored_in_cloud = True

            # ── Step 5: Insert DB record ─────────────────────────────────────
            _insert_generation_record(
                user_id=user_id,
                cleaned_text=cleaned_text,
                video_url=video_url,
            )

    finally:
        # ── Step 6: Cleanup local files ──────────────────────────────────────
        # Always runs — even if upload or DB insert raised an exception.
        # temp_files (uploaded face + audio) are ALWAYS deleted regardless of outcome.
        # Only delete generated video locally if it was successfully uploaded to cloud.
        if temp_files:
            _cleanup_local_files(*temp_files)   # user uploads — always delete

        if stored_in_cloud:
            _cleanup_local_files(local_video_path, local_voice_path)
        else:
            # Keep local video as fallback — don't delete if cloud failed
            print(f"[cleanup] Keeping local video (cloud upload failed): {local_video_path}")
            if local_voice_path:
                _cleanup_local_files(local_voice_path)  # voice always deletable

    return GenerateResponse(
        status="success",
        video_url=video_url,
        stored_in_cloud=stored_in_cloud,
        user_id=user_id,
        original_text=raw_text,
        cleaned_text=cleaned_text,
        cleaning_applied=(raw_text != cleaned_text),
        cleaning_steps=["LLM normalization via Azure OpenAI"] if raw_text != cleaned_text else [],
        char_delta=len(raw_text) - len(cleaned_text),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@fastapi_app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "AI Avatar Pipeline API",
        "supabase_connected": supabase is not None,
    }


@fastapi_app.post("/generate", response_model=GenerateResponse)
async def generate_from_text(
    text: str = Form(..., description="Avatar script text"),
    user_id: str = Form(default="anonymous", description="Firebase UID from frontend"),
    face_file: UploadFile = File(..., description="Avatar face image (.jpg/.png)"),
    ref_audio_file: UploadFile = File(..., description="Reference voice audio (.wav/.mp3)"),
    output_dir: str = Form(default="output"),
    use_deployed: bool = Form(default=False),
):
    """
    Generate avatar video from a direct text string + uploaded face + audio.

    multipart/form-data fields:
      text           — avatar script (required)
      user_id        — Firebase UID (optional, default: anonymous)
      face_file      — face image upload (.jpg / .png)
      ref_audio_file — voice reference upload (.wav / .mp3)
      output_dir     — output directory (optional)
      use_deployed   — use deployed Modal app (optional)
    """
    # Save uploaded files to disk first — _run() needs local paths
    temp_face_path  = await _save_upload_to_disk(face_file,      output_dir)
    temp_audio_path = await _save_upload_to_disk(ref_audio_file, output_dir)

    return _run(
        raw_text=text,
        user_id=user_id,
        ref_audio=temp_audio_path,
        face=temp_face_path,
        output_dir=output_dir,
        voice_file=None,
        use_deployed=use_deployed,
        text_source="direct form text",
        temp_files=[temp_face_path, temp_audio_path],
    )


@fastapi_app.post("/generate-from-file", response_model=GenerateResponse)
async def generate_from_file(
    script_file: UploadFile = File(..., description=".txt file containing the avatar script"),
    face_file: UploadFile = File(..., description="Avatar face image (.jpg/.png)"),
    ref_audio_file: UploadFile = File(..., description="Reference voice audio (.wav/.mp3)"),
    user_id: str = Form(default="anonymous"),
    output_dir: str = Form(default="output"),
    use_deployed: bool = Form(default=False),
):
    """
    Generate avatar video from an uploaded .txt script + face image + voice audio.

    multipart/form-data fields:
      script_file    — .txt file with avatar script (required)
      face_file      — face image upload (.jpg / .png) (required)
      ref_audio_file — voice reference upload (.wav / .mp3) (required)
      user_id        — Firebase UID (optional)
      output_dir     — output directory (optional)
      use_deployed   — use deployed Modal app (optional)
    """
    # ── Validate and read the script .txt file ───────────────────────────────
    if not script_file.filename:
        raise HTTPException(status_code=400, detail="No script file provided.")

    if not script_file.filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail=f"Only .txt script files accepted. Got: '{script_file.filename}'"
        )

    try:
        raw_bytes = await script_file.read()
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Script file encoding error. Please save your .txt file as UTF-8."
        )

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Script file is empty.")

    print(f"\n[upload] Script  : {script_file.filename}")
    print(f"[upload] Size    : {len(raw_bytes)} bytes")
    print(f"[upload] Lines   : {raw_text.count(chr(10)) + 1}")
    print(f"[upload] user_id : {user_id}")

    # ── Save face + audio uploads to disk ────────────────────────────────────
    temp_face_path  = await _save_upload_to_disk(face_file,      output_dir)
    temp_audio_path = await _save_upload_to_disk(ref_audio_file, output_dir)

    return _run(
        raw_text=raw_text,
        user_id=user_id,
        ref_audio=temp_audio_path,
        face=temp_face_path,
        output_dir=output_dir,
        voice_file=None,
        use_deployed=use_deployed,
        text_source=f"uploaded script: {script_file.filename}",
        temp_files=[temp_face_path, temp_audio_path],
    )


@fastapi_app.get("/video/{filename}")
def download_video(filename: str):
    """Download a locally stored video by filename (fallback if Supabase is not configured)."""
    safe_name = Path(filename).name
    video_path = Path("output") / safe_name

    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Video not found locally: '{safe_name}'. It may have been uploaded to Supabase cloud."
        )

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=safe_name,
    )


# @fastapi_app.get("/history/{user_id}")
# def get_user_history(user_id: str, limit: int = 10):
#     """
#     Fetch generation history for a user from Supabase DB.

#     Returns last `limit` generations (default 10), newest first.
#     """
#     if supabase is None:
#         raise HTTPException(
#             status_code=503,
#             detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY in .env"
#         )

#     try:
#         response = (
#             supabase.table("generations")
#             .select("id, user_id, text_used, video_url, created_at")
#             .eq("user_id", user_id)
#             .order("created_at", desc=True)
#             .limit(limit)
#             .execute()
#         )
#         return {"status": "ok", "user_id": user_id, "records": response.data}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"DB query failed: {str(e)}")

@fastapi_app.get("/history/{user_id}")
def get_user_history(user_id: str, limit: int = 10):
    """
    Fetch generation history for a user from Supabase DB.

    Returns last `limit` generations (default 10), newest first.
    Only returns records whose video still exists in Supabase Storage.
    Orphan DB records (video deleted from storage) are auto-cleaned up.
    """
    if supabase is None:
        raise HTTPException(
            status_code=503,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY in .env"
        )

    from urllib.parse import unquote

    try:
        response = (
            supabase.table("generations")
            .select("id, user_id, text_used, video_url, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        valid_records = []
        orphan_ids = []

        for record in response.data:
            try:
                # Storage path extract karo public URL se
                # URL format: .../public/avatars/Adeel%20Riaz/avatar_xxx.mp4
                storage_path = record["video_url"].split("/public/avatars/")[1]
                folder   = unquote(storage_path.rsplit("/", 1)[0])   # "Adeel Riaz"
                filename = unquote(storage_path.rsplit("/", 1)[1])   # "avatar_xxx.mp4"

                # Supabase storage mein folder list karo (decoded path)
                files = supabase.storage.from_("avatars").list(folder)
                file_names = [f["name"] for f in files] if files else []

                if filename in file_names:
                    valid_records.append(record)
                else:
                    orphan_ids.append(record["id"])

            except Exception:
                # URL parse na ho sake toh record skip karo
                orphan_ids.append(record["id"])

        # Orphan DB records cleanup — video storage mein nahi hai toh DB se bhi hatao
        for orphan_id in orphan_ids:
            try:
                supabase.table("generations").delete().eq("id", orphan_id).execute()
                print(f"[history] Orphan record deleted from DB: {orphan_id}")
            except Exception as e:
                print(f"[history] Could not delete orphan record {orphan_id}: {e}")

        return {"status": "ok", "user_id": user_id, "records": valid_records}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB query failed: {str(e)}")