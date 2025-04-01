import os
import io
import json
from flask import Flask, redirect, request, render_template, Response
from google.cloud import storage
import google.generativeai as genai
from PIL import Image

app = Flask(__name__)

# Initialize Google Cloud Storage client
storage_client = storage.Client()
BUCKET_NAME = 'my-images-upload'  
bucket = storage_client.bucket(BUCKET_NAME)

# Initialize Gemini API
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-1.5-flash')  # Or another suitable model

PROMPT = "Generate simple title and description for this image is JSON format." 


def upload_to_gemini(path, mime_type=None):
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    # print(file)
    return file

@app.route('/')
def index():
    index_html="""
<form method="post" enctype="multipart/form-data" action="/upload" method="post">
  <div>
    <label for="file">Choose file to upload</label>
    <input type="file" id="file" name="form_file" accept="image/jpeg"/>
  </div>
  <div>
    <button>Submit</button>
  </div>
</form>"""    

    for file in list_files():
        index_html += "<li><a href=\"/files/" + file + "\">" + file + "</a></li>"

    return index_html

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['form_file']

    filename = file.filename

    # Upload file to Google Cloud Storage
    blob = bucket.blob(filename)
    image_data = file.read()
    blob.upload_from_string(
        image_data,
        content_type=file.content_type
    )

    file.save(os.path.join("",file.filename))
    response = model.generate_content(
    [Image.open(file),PROMPT]
    )

    print(response.text)
    left_index=response.text.index("{")
    right_index=response.text.index("}")
    json_string=response.text[left_index:right_index +1]
    print(json_string)
    json_response=json.loads(json_string)
    with open(file.filename.split(".")[0]+".json","w") as f:
        json.dump(json_response,f,indent=4)
    blob = bucket.blob(file.filename.split(".")[0]+".json")
    blob.upload_from_filename(file.filename.split(".")[0]+".json")
    os.remove(file.filename.split(".")[0]+".json")
    os.remove(file.filename)
    

    return redirect("/")
    
@app.route('/files')
def list_files():
    files = []
    blobs = storage_client.list_blobs(BUCKET_NAME)
    for blob in blobs:
        files.append(blob.name)
    files = files
    jpegs = []
    for file in files:
        if file.lower().endswith(".jpeg") or file.lower().endswith(".jpg"):
            jpegs.append(file)
    
    return jpegs

@app.route('/files/<filename>')
def get_file(filename):
    blob = bucket.blob(filename.split(".")[0]+".json")
    file_data = blob.download_as_bytes()
    json_string=file_data.decode("utf-8")
    json_str=json.loads(json_string)
    print(json_str,type(json_str))
    html=f"""
    <body>
    <img src = "/images/{filename}">
    <p>Title:{json_str["title"]}</p>
    <p>Description:{json_str["description"]}</p>
    </body>
    """
    return html

@app.route('/images/<filename>')
def view_image(filename):
    blob = bucket.blob(filename)
    file_data = blob.download_as_bytes()
    return Response(io.BytesIO(file_data), mimetype='image/jpeg')

if __name__ == '__main__':
    app.run(host='localhost', port=5019,debug=True)
