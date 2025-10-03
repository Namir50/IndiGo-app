import os
from flask import Flask, request, render_template
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Load API keys
load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Folders
UPLOAD_FOLDER = "inputs"
OUTPUT_FOLDER = "outputs/images"
LOGO_PATH = "assets/indigo_logo.png"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)

# ---- ROUTES ----
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Save user selfie
        selfie = request.files["face"]
        selfie_path = os.path.join(UPLOAD_FOLDER, selfie.filename)
        selfie.save(selfie_path)

        # Load face + logo
        with open(selfie_path, "rb") as f:
            face_data = f.read()
        with open(LOGO_PATH, "rb") as f:
            logo_data = f.read()

        # Prompt
        prompt = (
            "Generate an ultra-realistic cinematic image of a skydiver diving "
            "from a jet painted in IndiGo Airlines livery. Use the provided face photo "
            "for the diver's identity, and apply the IndiGo logo onto the airplane. "
            "Show the diver mid-air, arms spread wide, with blue sky and clouds in the background."
        )

        # Call Gemini Flash 2.5 (Nano Banana)
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[
                prompt,
                types.Part(inline_data=types.Blob(mime_type="image/png", data=face_data)),
                types.Part(inline_data=types.Blob(mime_type="image/png", data=logo_data)),
            ],
        )

        # Save result(s)
        image_paths = []
        i = 1
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                img = Image.open(BytesIO(part.inline_data.data))
                out_path = os.path.join(OUTPUT_FOLDER, f"indigo_{i}.png")
                img.save(out_path)
                image_paths.append(out_path)
                i += 1

        return render_template("result.html", images=image_paths)

    return render_template("index.html")
