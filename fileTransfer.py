import os
import qrcode
from flask import Flask, request, send_from_directory, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shared_files')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def cleanup_old_files():
    qr_code_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qr_code.png")
    
    if os.path.exists(qr_code_path):
        os.remove(qr_code_path)
    
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

cleanup_old_files()

@app.route("/")
def home():
    return render_template("basicWebpage.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "files" not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files found in the request"}), 400

    for file in files:
        file.save(os.path.join(UPLOAD_FOLDER, file.filename))

    return jsonify({"message": "Files uploaded successfully"}), 200

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route("/files")
def list_files():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify({"files": files})

@app.route("/qr")
def generate_qr():
    url = request.host_url
    img = qrcode.make(url)
    qr_code_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qr_code.png")
    img.save(qr_code_path)
    
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "qr_code.png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
