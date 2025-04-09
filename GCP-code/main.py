import os
import subprocess
from flask import Flask, request, jsonify
from google.cloud import storage

# Initialize Flask
app = Flask(__name__)

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket_name = "your_bucket_name_here"  # Replace with your bucket name
bucket = storage_client.bucket(bucket_name)

# Set temporary directory for files
TEMP_DIR = "/tmp"

@app.route("/", methods=["GET"])
def home():
    return "🚀 Video Editor API is Running!", 200

@app.route("/process", methods=["POST"])
def process_video():
    try:
        # Read parameters from request
        data = request.get_json()
        image_url = data.get("image")
        audio_url = data.get("audio")
        output_url = data.get("output")

        # Check if parameters are provided
        if not image_url or not audio_url or not output_url:
            return jsonify({"error": "Parameters 'image', 'audio', and 'output' are required!"}), 400

        # Extract file names
        image_name = os.path.basename(image_url)
        audio_name = os.path.basename(audio_url)
        output_name = os.path.basename(output_url)

        # Set local paths
        image_path = os.path.join(TEMP_DIR, image_name)
        audio_path = os.path.join(TEMP_DIR, audio_name)
        output_path = os.path.join(TEMP_DIR, output_name)

        # Download files from GCS
        bucket.blob(image_name).download_to_filename(image_path)
        bucket.blob(audio_name).download_to_filename(audio_path)

        # Check if ffmpeg is installed
        try:
            subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("FFmpeg is installed and working!")
        except Exception as e:
            return jsonify({"error": f"FFmpeg not found: {e}"}), 500

        # Execute FFmpeg command to merge image and audio into a video
        command = [
            "ffmpeg", "-loop", "1", "-i", image_path, "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", output_path
        ]
        subprocess.run(command, check=True)

        # Upload resulting file to GCS
        output_blob = bucket.blob(output_name)
        output_blob.upload_from_filename(output_path)

        # Return link to processed file
        return jsonify({"message": "Video created successfully!", "output": f"gs://{bucket_name}/{output_name}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
