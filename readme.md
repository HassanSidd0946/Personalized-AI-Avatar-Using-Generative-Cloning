# AvatarClone

An event-driven, microservices-based AI pipeline that generates high-fidelity, lip-synced digital avatars using zero-shot voice cloning.

AvatarClone takes a static image and a text/audio prompt, processes them through a decoupled cloud-GPU pipeline, and returns a high-definition video of the avatar speaking the prompt with perfect temporal synchronization.

## Features

- **Zero-Shot Voice Cloning:** Clone voices from as little as a 6-second audio sample without fine-tuning.
- **Accurate Lip-Syncing:** Frame-by-frame temporal synchronization using specialized GAN discriminators.
- **HD Face Restoration:** Automated upscaling and artifact removal to maintain facial clarity.
- **Serverless GPU Inference:** Highly scalable, cost-optimized execution on demand.
- **Event-Driven Microservices:** Decoupled architecture ensuring no single point of failure between UI, API, and Inference layers.

## System Architecture

The project is structured into four distinct layers following the Separation of Concerns principle:

1. **Presentation Layer:** React-based frontend hosted on Vercel for user input and video rendering.
2. **API Gateway & Orchestration Layer:** Lightweight FastAPI backend handling request validation, routing, and asynchronous API calls (exposed securely via ngrok).
3. **Data Persistence Layer:** Supabase integration for unstructured blob storage (images/videos) and relational metadata logging.
4. **Compute / Inference Layer:** Modal Labs serverless A100/T4 GPUs executing the core deep learning pipeline.

### Core AI Pipeline

The compute layer runs a sequential pipeline:

1. **XTTS v2:** Extracts speaker embeddings and generates autoregressive text-to-speech audio.
2. **Wav2Lip:** Syncs the generated audio with the static input image to produce a raw lip-synced video.
3. **GFPGAN (Generative Facial Prior):** Injects high-definition facial priors to restore and upscale the blurry output from the Wav2Lip model.

## Tech Stack

- **Backend & API:** Python 3.12, FastAPI, ngrok
- **AI / Deep Learning:** XTTS v2 (Coqui), Wav2Lip, GFPGAN
- **Cloud Infrastructure:** Modal.com (Serverless GPUs)
- **Frontend:** React.js, Vercel
- **Database & Storage:** Supabase (PostgreSQL & Object Storage)

## Local Development Setup

We use standard Python 3.12 for local backend development (Anaconda is not required/used).

1. Clone the repository:

```bash
git clone https://github.com/HassanSidd0946/Personalized-AI-Avatar-Using-Generative-Cloning.git
cd AvatarClone
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up your `.env` file with your Modal tokens, Supabase keys, and ngrok auth token.

5. Run the FastAPI server:

```bash
uvicorn main:app --reload
```
