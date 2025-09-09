import os
import zipfile
import qrcode
from flask import Flask, request, send_from_directory, jsonify, render_template, send_file
from flask_cors import CORS
import concurrent.futures
from io import BytesIO
import shutil
import tempfile

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
    
    # Clean up all files and folders in upload directory
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

cleanup_old_files()

@app.route("/")
def home():
    return render_template("basicWebpage.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    # Check if any files were uploaded
    if not request.files:
        return jsonify({"error": "No files uploaded"}), 400

    upload_tasks = []
    uploaded_files = []
    
    # Handle both regular file uploads and folder uploads
    for key in request.files:
        files = request.files.getlist(key)
        for file in files:
            if file.filename:  # Only process if file has a name
                uploaded_files.append(file)
    
    if not uploaded_files:
        return jsonify({"error": "No valid files selected"}), 400

    for file in uploaded_files:
        # Check if this is from a folder upload (has webkit relative path)
        content_disposition = file.headers.get('Content-Disposition', '')
        relative_path = extract_relative_path(content_disposition, file.filename)
        
        if relative_path:
            # This is from a folder upload, preserve directory structure
            task = executor.submit(save_file_with_structure, file, relative_path)
        else:
            # Regular file upload
            task = executor.submit(save_file, file)
        upload_tasks.append(task)
    
    # Wait for all uploads to complete
    for task in upload_tasks:
        task.result()

    return jsonify({"message": f"{len(uploaded_files)} files uploaded successfully"}), 200

def extract_relative_path(content_disposition, filename):
    """Extract relative path from webkitdirectory file upload"""
    if not content_disposition or 'webkitrelativepath' not in content_disposition.lower():
        return ""
    
    try:
        # Extract the relative path from Content-Disposition header
        parts = content_disposition.split(';')
        for part in parts:
            part = part.strip()
            if part.lower().startswith('webkitrelativepath'):
                path_value = part.split('=', 1)[1].strip().strip('"')
                # Return the full path including filename
                return path_value
    except Exception as e:
        print(f"Error extracting relative path: {e}")
    
    return ""

def save_file(file):
    """Save a regular file to upload directory"""
    # Sanitize filename
    filename = "".join(c for c in file.filename if c.isprintable() and c not in ['/', '\\', ':', '*', '?', '"', '<', '>', '|'])
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    print(f"Saved file: {filename}")
    return file_path

def save_file_with_structure(file, relative_path):
    """Save file with directory structure preserved"""
    if not relative_path:
        # Fallback to regular file upload if no relative path
        return save_file(file)
    
    # Sanitize path components
    safe_relative_path = "".join(c for c in relative_path if c.isprintable() and c not in ['..', ':', '*', '?', '"', '<', '>', '|'])
    
    # Get the directory portion of the path
    dir_path = os.path.dirname(safe_relative_path)
    
    # Create directory structure
    full_dir_path = os.path.join(UPLOAD_FOLDER, dir_path)
    os.makedirs(full_dir_path, exist_ok=True)
    
    # Get just the filename
    safe_filename = os.path.basename(safe_relative_path)
    safe_filename = "".join(c for c in safe_filename if c.isprintable() and c not in ['/', '\\', ':', '*', '?', '"', '<', '>', '|'])
    
    # Save file
    file_path = os.path.join(full_dir_path, safe_filename)
    file.save(file_path)
    print(f"Saved file with structure: {dir_path}/{safe_filename}")
    return file_path

@app.route("/download/<path:filename>")
def download_file(filename):
    """Download a file"""
    try:
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"File not found: {str(e)}"}), 404

@app.route("/download-zip")
def download_zip():
    """Download all files as a zip archive with proper folder structure"""
    # Check if there are any files
    if not any(os.path.isfile(os.path.join(UPLOAD_FOLDER, f)) or os.path.isdir(os.path.join(UPLOAD_FOLDER, f)) for f in os.listdir(UPLOAD_FOLDER)):
        return jsonify({"error": "No files available"}), 404
    
    # Determine the appropriate zip name based on content
    items = os.listdir(UPLOAD_FOLDER)
    zip_name = "shared_files"
    
    # If there's a single folder, use that as the zip name
    if len(items) == 1 and os.path.isdir(os.path.join(UPLOAD_FOLDER, items[0])):
        zip_name = items[0]
    # If there are multiple items, use a generic name
    elif len(items) > 1:
        zip_name = "all_files"
    
    # Create a temporary file for the zip
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_zip.close()
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(UPLOAD_FOLDER):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Create relative path for zip (preserving folder structure)
                    relative_path = os.path.relpath(file_path, UPLOAD_FOLDER)
                    zf.write(file_path, relative_path)
        
        return send_file(
            temp_zip.name,
            download_name=f'{zip_name}.zip',
            as_attachment=True,
            mimetype='application/zip'
        )
    finally:
        # Clean up the temporary file after sending
        os.unlink(temp_zip.name)

@app.route("/files")
def list_files():
    """List all available files with sizes"""
    file_list = []
    total_size = 0
    
    for root, dirs, files in os.walk(UPLOAD_FOLDER):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                size = os.path.getsize(file_path)
                total_size += size
                relative_path = os.path.relpath(file_path, UPLOAD_FOLDER)
                
                file_list.append({
                    "name": relative_path,
                    "size": size,
                    "size_formatted": format_file_size(size),
                    "is_directory": False
                })
            except OSError:
                continue
    
    # Also list empty directories
    for root, dirs, files in os.walk(UPLOAD_FOLDER):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            relative_path = os.path.relpath(dir_path, UPLOAD_FOLDER)
            file_list.append({
                "name": relative_path + "/",
                "size": 0,
                "size_formatted": "0 B",
                "is_directory": True
            })
    
    return jsonify({"files": file_list, "total_size": total_size})

def format_file_size(size_bytes):
    """Convert bytes to human-readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names)-1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"

@app.route("/create-folder", methods=["POST"])
def create_folder():
    """Create a new folder"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    
    folder_name = data.get("name", "").strip()
    if not folder_name:
        return jsonify({"error": "Folder name is required"}), 400
    
    # Sanitize folder name
    folder_name = "".join(c for c in folder_name if c.isprintable() and c not in ['/', '\\', ':', '*', '?', '"', '<', '>', '|'])
    folder_path = os.path.join(UPLOAD_FOLDER, folder_name)
    
    if os.path.exists(folder_path):
        return jsonify({"error": "Folder already exists"}), 400
    
    try:
        os.makedirs(folder_path, exist_ok=True)
        return jsonify({"message": f"Folder '{folder_name}' created successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to create folder: {str(e)}"}), 500

@app.route("/storage-info")
def storage_info():
    """Get storage information"""
    total, used, free = shutil.disk_usage(UPLOAD_FOLDER)
    
    # Calculate actual used space by our files
    uploaded_size = 0
    for root, dirs, files in os.walk(UPLOAD_FOLDER):
        for file in files:
            try:
                uploaded_size += os.path.getsize(os.path.join(root, file))
            except OSError:
                continue
    
    return jsonify({
        "total_disk": total,
        "used_disk": used,
        "free_disk": free,
        "uploaded_size": uploaded_size,
        "file_count": sum([len(files) for r, d, files in os.walk(UPLOAD_FOLDER)])
    })

@app.route("/qr")
def generate_qr():
    # Use the request host to generate QR code
    # For mobile compatibility, ensure we're using the correct URL
    url = request.host_url
    # Remove trailing slash for cleaner QR code
    if url.endswith('/'):
        url = url[:-1]
    
    img = qrcode.make(url)
    qr_code_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qr_code.png")
    img.save(qr_code_path)
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "qr_code.png")

@app.route("/cleanup", methods=["POST"])
def cleanup_files():
    """Clean up all files"""
    try:
        cleanup_old_files()
        # Recreate the upload directory
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        return jsonify({"message": "All files cleaned up successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # For mobile compatibility, ensure the server is accessible on the network
    app.run(host="0.0.0.0", port=8080, threaded=True, debug=True)
