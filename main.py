import os
from flask import Flask, redirect, request, render_template, Response
import io
from google.cloud import storage

app = Flask(__name__)

# Initialize Google Cloud Storage client
storage_client = storage.Client()
BUCKET_NAME ='my-images-upload'
bucket = storage_client.bucket(BUCKET_NAME)

@app.route('/', methods=['GET'])
def index():
    # List existing files from Google Cloud Storage
    blobs = bucket.list_blobs()
    files = [blob.name for blob in blobs if blob.name.lower().endswith(('.jpeg', '.jpg'))]
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['form_file']
    
    # Generate a unique filename to prevent overwrites
    filename = f"{file.filename}"
    
    # Upload file to Google Cloud Storage
    blob = bucket.blob(filename)
    blob.upload_from_string(
        file.read(), 
        content_type=file.content_type
    )
    
    return redirect("/")
    
@app.route('/files/<filename>')
def get_file(filename):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    file_data = blob.download_as_bytes()
    return Response(io.BytesIO(file_data), mimetype='image/jpeg')

if __name__ == '__main__':
    app.run(host='localhost', port=5003,debug=True)