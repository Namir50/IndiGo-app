import os
import httpx
import asyncio
from dotenv import load_dotenv
from flask import Flask, request, render_template

load_dotenv()

# ==== CONFIG ====
MIDJOURNEY_API_KEY = os.getenv("MIDJOURNEY_API_KEY")
UPLOAD_FOLDER = "inputs"

BASE_PROMPT = """An ultra-realistic, cinematic wide-angle photograph of a full-body skydiver diving out of a Saab 105 jet painted in IndiGo Airlines livery. 
              The IndiGo Airlines Saab 105 airplane is clearly visible in the same frame, positioned above and behind the diver. 
              The plane’s side passenger door is wide open, showing the exit point from which the diver just leapt, with sharp details of the open hatch, metallic textures, and the IndiGo logo and blue-and-white branding clearly visible along the fuselage. 
              The diver is captured in the foreground, entire body in frame, mid-dive in free fall with arms spread wide and legs extended dynamically against the wind. 
              He is not wearing a helmet his face is unobstructed, vividly showing an excited, adrenaline-filled expression of pure thrill and joy, eyes wide open and mouth smiling in exhilaration. 
              His hair is windswept, reacting naturally to the high-speed dive. His skin shows hyper-realistic detail visible pores, fine textures, and subtle imperfections enhanced by daylight HDR lighting. 
              The skydiving suit is a custom IndiGo Airlines jumpsuit in deep indigo blue with precise airline logos, livery patterns, and aerodynamic seams. The fabric appears thick and durable, with realistic folds and creases, rippling in the wind to emphasize motion. Light glints off metallic buckles and straps, adding authenticity. 
              The surrounding sky is bright and expansive, scattered with realistic fluffy white clouds, rendered with volumetric lighting. Subtle motion blur on the clouds and background sky conveys the immense speed and altitude of the dive, while the foreground diver remains sharply in focus. 
              The entire composition is cinematic and dramatic, balancing the diver in the foreground and the IndiGo Saab 105 aircraft with its open door in the background. 
              Photographed as if shot on an Arri Alexa 65 using a 35mm wide-angle lens, full HDR cinematic realism, natural daylight illumination, wide-body framing, hyper-detailed textures, 16:9 aspect ratio."""

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==== FLASK APP ====
app = Flask(__name__)

# -------- MidJourney API Wrapper --------
class MidjourneyAPI:
    def __init__(self, api_key):
        self.base_url = "https://api.piapi.ai/api/v1"
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    async def create_task(self, prompt, image_ref, aspect_ratio="16:9"):
        payload = {
            "model": "midjourney",
            "task_type": "imagine",
            "input": {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "process_mode": "turbo",
                "skip_prompt_check": False,
                "image_references": [image_ref]  # 👈 Add user selfie
            }
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}/task", headers=self.headers, json=payload)
            r.raise_for_status()
            return r.json()

    async def get_status(self, task_id):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/task/{task_id}", headers=self.headers)
            r.raise_for_status()
            return r.json()

async def generate_images(prompt, image_ref):
    api = MidjourneyAPI(MIDJOURNEY_API_KEY)
    task = await api.create_task(prompt, image_ref)
    task_id = task["data"]["task_id"]

    # Poll until complete
    import time
    start = time.time()
    while time.time() - start < 300:
        status = await api.get_status(task_id)
        if status["data"]["status"] == "completed":
            return status["data"]["output"]["image_urls"]
        elif status["data"]["status"] == "failed":
            raise RuntimeError("Image generation failed")
        await asyncio.sleep(5)
    raise TimeoutError("Image generation timed out")

# -------- Routes --------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        selfie = request.files["face"]
        selfie_path = os.path.join(UPLOAD_FOLDER, selfie.filename)
        selfie.save(selfie_path)

        # Call MidJourney with Omni Ref
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            image_urls = loop.run_until_complete(generate_images(BASE_PROMPT, selfie_path))
        finally:
            loop.close()

        return render_template("result.html", images=image_urls)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
