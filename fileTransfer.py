import os
import zipfile
import qrcode
from flask import Flask, request, send_from_directory, jsonify, render_template, send_file  # Added send_file here
from flask_cors import CORS
import concurrent.futures
from io import BytesIO

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shared_files')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Thread pool for parallel operations
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

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

    # Process files in parallel using thread pool
    upload_tasks = []
    for file in files:
        task = executor.submit(save_file, file)
        upload_tasks.append(task)
    
    # Wait for all uploads to complete
    for task in upload_tasks:
        task.result()

    return jsonify({"message": "Files uploaded successfully"}), 200

def save_file(file):
    """Save a single file to the upload directory"""
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    return file_path

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route("/download-zip")
def download_zip():
    """Download all files as a zip archive for faster batch downloads"""
    files = os.listdir(UPLOAD_FOLDER)
    if not files:
        return jsonify({"error": "No files available"}), 404
    
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            file_path = os.path.join(UPLOAD_FOLDER, file)
            zf.write(file_path, file)
    
    memory_file.seek(0)
    return send_file(
        memory_file,
        download_name='shared_files.zip',
        as_attachment=True
    )

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

@app.route("/cleanup", methods=["POST"])
def cleanup_files():
    """API endpoint to clean up all files"""
    try:
        cleanup_old_files()
        return jsonify({"message": "All files cleaned up successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
