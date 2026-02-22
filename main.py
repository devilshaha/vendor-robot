from fastapi import FastAPI, UploadFile, File, HTTPException
from sqlalchemy import create_engine, text
import os
import uuid
import boto3
import openai
from pypdf import PdfReader
from io import BytesIO

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_BUCKET = os.getenv("R2_BUCKET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

engine = create_engine(DATABASE_URL)
openai.api_key = OPENAI_API_KEY

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    key = f"{uuid.uuid4()}_{file.filename}"

    s3.put_object(Bucket=R2_BUCKET, Key=key, Body=data)

    reader = PdfReader(BytesIO(data))
    text_content = ""
    for page in reader.pages:
        text_content += page.extract_text() or ""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Extract vendor document type and key fields as JSON"},
            {"role": "user", "content": text_content[:12000]}
        ]
    )

    return {
        "file": file.filename,
        "analysis": response.choices[0].message.content
    }
from fastapi.responses import HTMLResponse

@app.get("/")
def home():
    return HTMLResponse("""
    <html>
        <body>
            <h2>Vendor Robot – Upload Document</h2>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file"/>
                <br/><br/>
                <button type="submit">Upload</button>
            </form>
        </body>
    </html>
    """)
