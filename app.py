from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory, flash, abort, jsonify
import os
import socket
from datetime import datetime
import secrets
import io
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configuration
# Always resolve uploads folder relative to the app root to avoid CWD issues across devices/executables
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
CHUNKS_FOLDER = os.path.join(UPLOAD_FOLDER, '.chunks')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'mp3', 'mp4'}
# Configurable max size (MB). Set MAX_FILE_SIZE_MB=0 to allow unlimited (not recommended on untrusted networks)
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '4096'))  # 4 GB default
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024 if MAX_FILE_SIZE_MB > 0 else None

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if MAX_FILE_SIZE is not None:
    app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
else:
    # Remove limit if explicitly set to unlimited
    app.config.pop('MAX_CONTENT_LENGTH', None)

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHUNKS_FOLDER, exist_ok=True)

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        # Connect to a remote address to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size(file_path):
    """Get file size in human readable format"""
    size = os.path.getsize(file_path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GB"

def get_files_info():
    """Get information about all uploaded files"""
    files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            stat = os.stat(file_path)
            files.append({
                'name': filename,
                'size': get_file_size(file_path),
                'upload_time': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'path': file_path
            })
    return sorted(files, key=lambda x: x['upload_time'], reverse=True)

def _safe_destination_name(filename: str) -> str:
    """Ensure destination filename doesn't overwrite unintentionally by appending a counter if exists."""
    base = secure_filename(filename)
    if not base:
        base = f"upload-{secrets.token_hex(4)}"
    name, ext = os.path.splitext(base)
    dest = os.path.join(app.config['UPLOAD_FOLDER'], base)
    counter = 1
    while os.path.exists(dest):
        dest = os.path.join(app.config['UPLOAD_FOLDER'], f"{name} ({counter}){ext}")
        counter += 1
    return os.path.basename(dest)

@app.route('/')
def index():
    files = get_files_info()
    local_ip = get_local_ip()
    port = 5000  # Default Flask port
    share_url = f"http://{local_ip}:{port}"
    max_size_display = f"{MAX_FILE_SIZE_MB}MB" if MAX_FILE_SIZE_MB > 0 else "Unlimited"
    return render_template(
        'index.html',
        files=files,
        share_url=share_url,
        allowed_extensions=sorted(ALLOWED_EXTENSIONS),
        max_size_display=max_size_display,
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        # Sanitize filename for safety across OS/browsers
        filename = _safe_destination_name(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        flash(f'File "{filename}" uploaded successfully!', 'success')
    else:
        flash('File type not allowed', 'error')
    
    return redirect(url_for('index'))

# --------- Chunked upload endpoints ---------
@app.route('/upload/init', methods=['POST'])
def upload_init():
    data = request.get_json(silent=True) or {}
    filename = data.get('filename', '')
    total_size = int(data.get('size') or 0)

    if not filename:
        return jsonify({"ok": False, "error": "Missing filename"}), 400
    if not allowed_file(filename):
        return jsonify({"ok": False, "error": "File type not allowed"}), 400
    if MAX_FILE_SIZE is not None and total_size > MAX_FILE_SIZE:
        # Simulate 413 for chunked flow
        return jsonify({"ok": False, "error": f"File too large. Max {int(MAX_FILE_SIZE / (1024*1024))}MB"}), 413

    upload_id = secrets.token_hex(16)
    session_dir = os.path.join(CHUNKS_FOLDER, upload_id)
    os.makedirs(session_dir, exist_ok=True)
    # Store metadata
    meta = {
        "filename": secure_filename(filename),
        "size": total_size,
    }
    with open(os.path.join(session_dir, 'meta.json'), 'w', encoding='utf-8') as f:
        import json
        json.dump(meta, f)

    return jsonify({"ok": True, "upload_id": upload_id})


@app.route('/upload/chunk', methods=['POST'])
def upload_chunk():
    upload_id = request.form.get('upload_id')
    chunk_index = request.form.get('chunk_index')
    total_chunks = request.form.get('total_chunks')
    filename = request.form.get('filename')
    chunk = request.files.get('chunk')

    try:
        chunk_index = int(chunk_index)
        total_chunks = int(total_chunks)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid chunk indices"}), 400

    if not upload_id or chunk is None or filename is None:
        return jsonify({"ok": False, "error": "Missing parameters"}), 400

    session_dir = os.path.join(CHUNKS_FOLDER, upload_id)
    if not os.path.isdir(session_dir):
        return jsonify({"ok": False, "error": "Invalid upload session"}), 400

    # Save chunk
    chunk_path = os.path.join(session_dir, f"chunk_{chunk_index:06d}.part")
    chunk.save(chunk_path)

    return jsonify({"ok": True, "received": chunk_index, "total": total_chunks})


@app.route('/upload/complete', methods=['POST'])
def upload_complete():
    data = request.get_json(silent=True) or {}
    upload_id = data.get('upload_id')
    if not upload_id:
        return jsonify({"ok": False, "error": "Missing upload_id"}), 400

    import json
    session_dir = os.path.join(CHUNKS_FOLDER, upload_id)
    if not os.path.isdir(session_dir):
        return jsonify({"ok": False, "error": "Invalid upload session"}), 400

    meta_path = os.path.join(session_dir, 'meta.json')
    if not os.path.isfile(meta_path):
        return jsonify({"ok": False, "error": "Missing metadata"}), 400

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    final_name = _safe_destination_name(meta.get('filename') or f"upload-{upload_id}")
    dest_path = os.path.join(app.config['UPLOAD_FOLDER'], final_name)

    # Merge chunks in order
    chunk_files = sorted(
        [fn for fn in os.listdir(session_dir) if fn.startswith('chunk_') and fn.endswith('.part')]
    )
    if not chunk_files:
        return jsonify({"ok": False, "error": "No chunks uploaded"}), 400

    with open(dest_path, 'wb') as dest:
        for cf in chunk_files:
            cpath = os.path.join(session_dir, cf)
            with open(cpath, 'rb') as src:
                while True:
                    buf = src.read(1024 * 1024)
                    if not buf:
                        break
                    dest.write(buf)

    # Cleanup
    try:
        import shutil
        shutil.rmtree(session_dir, ignore_errors=True)
    except Exception:
        pass

    return jsonify({"ok": True, "filename": final_name})

@app.route('/download/<path:filename>')
def download_file(filename):
    # Use send_from_directory for safer, more reliable file serving
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(file_path):
        flash('File not found', 'error')
        return redirect(url_for('index'))
    # as_attachment forces a download dialog
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True, conditional=True)

@app.route('/view/<path:filename>')
def view_file(filename):
    """Serve file inline to be viewable in the browser (no forced download)."""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(file_path):
        flash('File not found', 'error')
        return redirect(url_for('index'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False, conditional=True)


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    # Friendly error when file exceeds MAX_CONTENT_LENGTH
    limit = f"{MAX_FILE_SIZE_MB}MB" if MAX_FILE_SIZE_MB > 0 else "unlimited"
    flash(f"File is too large. The current upload limit is {limit}.", 'error')
    return redirect(url_for('index'))

@app.route('/delete/<filename>')
def delete_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f'File "{filename}" deleted successfully!', 'success')
    else:
        flash('File not found', 'error')
    return redirect(url_for('index'))

@app.route('/share')
def share():
    local_ip = get_local_ip()
    port = 5000
    share_url = f"http://{local_ip}:{port}"
    return render_template('share.html', share_url=share_url, local_ip=local_ip, port=port)


@app.route('/qr')
def qr_code():
    """Return a QR code image (SVG) for the provided text or the default share URL.
    If the 'qrcode' package is unavailable, return 501 to allow client fallback.
    """
    text = request.args.get('text')
    if not text:
        # Default to share URL
        local_ip = get_local_ip()
        text = f"http://{local_ip}:5000"
    try:
        import qrcode
        import qrcode.image.svg as qrc_svg
        factory = qrc_svg.SvgImage
        img = qrcode.make(text, image_factory=factory, box_size=10, border=2)
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        return send_file(buf, mimetype='image/svg+xml')
    except Exception:
        # Signal the client to use a fallback QR generator (handled via onerror in the img tag)
        return ("QR generation not available", 501, {"Content-Type": "text/plain"})

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"\n=== File Sharing App ===")
    print(f"Local URL: http://127.0.0.1:5000")
    print(f"Network URL: http://{local_ip}:5000")
    print(f"Share this URL with others on the same WiFi network!")
    print("========================\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)