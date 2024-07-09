import os
import tempfile
import pandas as pd
import mysql.connector
from flask import Flask, request, redirect, url_for, send_file, render_template
from google.cloud import vision
import fitz  # PyMuPDF

# Set the environment variable for Google Cloud Vision API
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'D:/Projects/Final Year projects/rohini/Teralogic Task/vilearnxtech-2b36141dddf9.json'

# Initialize the Google Cloud Vision client
client = vision.ImageAnnotatorClient()

app = Flask(__name__)

def extract_text_from_image(file_path):
    with open(file_path, 'rb') as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    
    if response.error.message:
        raise Exception(f'{response.error.message}')
    
    return response.full_text_annotation.text

def extract_text_from_pdf(file_path):
    text = ''
    pdf_document = fitz.open(file_path)
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        text += page.get_text("text")
    return text

def process_extracted_data(text):
    lines = text.split('\n')
    data = {'Line Number': range(1, len(lines) + 1), 'Content': lines}
    df = pd.DataFrame(data)
    return df

def save_to_database(df, db_config):
    # Connect to the MySQL database
    conn = mysql.connector.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database']
    )
    cursor = conn.cursor()

    # Insert data into the database
    for _, row in df.iterrows():
        cursor.execute(
            "INSERT INTO extracted_data (line_number, content) VALUES (%s, %s)",
            (row['Line Number'], row['Content'])
        )
    
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files[]' not in request.files:
        return redirect(request.url)
    
    files = request.files.getlist('files[]')
    all_texts = []

    temp_dir = tempfile.mkdtemp()
    
    for file in files:
        if file.filename == '':
            continue
        
        file_path = os.path.join(temp_dir, file.filename)
        file.save(file_path)
        
        if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            text = extract_text_from_image(file_path)
        elif file.filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        else:
            continue
        
        all_texts.append(text)
    
    combined_text = "\n".join(all_texts)
    df = process_extracted_data(combined_text)
    
    # Save DataFrame to a temporary CSV file
    csv_path = os.path.join(temp_dir, 'extracted_data.csv')
    df.to_csv(csv_path, index=False)
    
    # Save to database
    db_config = {
        'host': 'srv921.hstgr.io',
        'user': 'u329799078_Teralogic_task',
        'password': 'Subburs987@',
        'database': 'u329799078_Teralogic_task'
    }
    save_to_database(df, db_config)
    
    return send_file(csv_path, as_attachment=True, download_name='extracted_data.csv')

if __name__ == '__main__':
    app.run(debug=True)
