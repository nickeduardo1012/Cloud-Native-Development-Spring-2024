import os
from flask import Flask, redirect, request, send_file, Response
from google.cloud import storage
import google.generativeai as genai
import json
import io

BUCKET_NAME = "my-images-upload"
storage_client = storage.Client()

os.makedirs('files', exist_ok = True)

app = Flask(__name__)


def get_list_of_files(bucket_name):
    """Lists all the blobs in the bucket."""
    print("\n")
    print("get_list_of_files: "+bucket_name)

    blobs = storage_client.list_blobs(bucket_name)
    print(blobs)
    files = []
    for blob in blobs:
        files.append(blob.name)

    return files

def upload_file(bucket_name, file_name):
    """Send file to bucket."""
    print("\n")
    print("upload_file: "+bucket_name+"/"+file_name)

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    blob.upload_from_filename(file_name)

    return 

def download_file(bucket_name, file_name):
    """ Retrieve an object from a bucket and saves locally"""  
    print("\n")
    print("download_file: "+bucket_name+"/"+file_name)
    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(file_name)
    blob.download_to_filename('files/'+file_name)
    blob.reload()
   
    return

genai.configure(api_key=os.environ['GEMINI_API_KEY'])


generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "application/json",
}

PROMPT = "Generate a simple title and description for this image in json format"

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",

)

def upload_to_gemini(path, mime_type=None):
  """Uploads the given file to Gemini.

  See https://ai.google.dev/gemini-api/docs/prompting_with_media
  """
  file = genai.upload_file(path, mime_type=mime_type)
  print(f"Uploaded file '{file.display_name}' as: {file.uri}")
  # print(file)
  return file


@app.route('/')
def index():
    index_html="""
<form method="post" enctype="multipart/form-data" action="/upload" method="post">
<body style="background-color:white;">
  <div>
    <label for="file">Choose file to upload</label>
    <input type="file" id="file" name="form_file" accept="image/jpeg"/>
  </div>
  <div>
    <button>Submit</button>
  </div>
  </body>
</form>"""    

    for file in list_files():
        index_html += "<li><a href=\"/files/" + file + "\">" + file + "</a></li>"

    return index_html

@app.route('/upload', methods=["POST"])
def upload():
    file = request.files['form_file']  
    file.save(file.filename)
    response = model.generate_content(
    [upload_to_gemini(file.filename, mime_type="image/jpeg"), PROMPT]
    )
    print(response.text)
    left_index=response.text.index("{")
    right_index=response.text.index("}")
    json_string=response.text[left_index:right_index+1]
    print(json_string)
    json_response=json.loads(json_string)
    print(json_response)

    upload_file(BUCKET_NAME, file.filename)

    with open(file.filename.split(".")[0]+".json", "w") as f:
      json.dump(json_response,f)
    upload_file(BUCKET_NAME, file.filename.split(".")[0]+".json")



    return redirect("/")

@app.route('/files')
def list_files():
    files = get_list_of_files(BUCKET_NAME)
    jpegs = []
    for file in files:
        if file.lower().endswith(".jpeg") or file.lower().endswith(".jpg"):
            jpegs.append(file)
    
    return jpegs
    
@app.route('/files/<filename>')
def get_file(filename):

  bucket=storage_client.bucket(BUCKET_NAME)
  blob=bucket.blob(filename.split(".")[0]+".json")
  file_data=blob.download_as_bytes()
  json_string=file_data.decode("UTF-8")
  json_string=json.loads(json_string)


  image_html=f"""
  <img src = "/images/{filename}">
  <p> Title: {json_string["title"]}<p>
  <p> Description: {json_string["description"]}<p>
"""   
 
  return image_html

@app.route('/images/<imagename>')
def get_image(imagename):
  bucket=storage_client.bucket(BUCKET_NAME)
  blob=bucket.blob(imagename)
  file_data=blob.download_as_bytes()

  return Response(io.BytesIO(file_data), mimetype='image/jpeg')



if __name__ == '__main__':
    app.run(debug=True)
