# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import PyPDF2
import pandas as pd
import re
import os
import pytesseract
from pdf2image import convert_from_path

# Set the path to the Tesseract OCR executable
# Adjust this path based on your Tesseract installation location
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Function to clean extracted text
def clean_text(text):
    if not isinstance(text, str):
        text = str(text)  # Ensure it's a string
    # Remove NULL bytes and control characters
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    return text

# Specify the directory containing PDF files
pdf_directory = 'C:/Users/rahul_borse/Python'
excel_file_path = 'C:/Users/rahul_borse/Python/output.xlsx'

# Initialize a list to hold the extracted and cleaned text from all PDFs
text_data = []

# Iterate over all files in the specified directory
for filename in os.listdir(pdf_directory):
    if filename.endswith('.pdf'):  # Check if the file is a PDF
        pdf_file_path = os.path.join(pdf_directory, filename)
        print(f"Processing {filename}...")  # Debug statement
        try:
            with open(pdf_file_path, 'rb') as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)

                # Flag to check if text was extracted
                text_extracted = False

                # Iterate through each page of the PDF
                for page in reader.pages:
                    text = page.extract_text()  # Extract text from the page
                    if text:  # Check if text was extracted
                        cleaned_text = clean_text(text)  # Clean the extracted text
                        if cleaned_text:  # Only append if there's valid cleaned text
                            text_data.append([cleaned_text])  # Append the cleaned text
                            text_extracted = True

                # If no text was extracted, use OCR
                if not text_extracted:
                    print("No text found, using OCR...")
                    images = convert_from_path(pdf_file_path)
                    for i, image in enumerate(images):
                        text = pytesseract.image_to_string(image)
                        cleaned_text = clean_text(text)
                        if cleaned_text:
                            text_data.append([cleaned_text])  # Append cleaned text from OCR

        except Exception as e:
            print(f"An error occurred while processing {filename}: {e}")

# Create a DataFrame from the list
if text_data:  # Check if there's any data to write
    df = pd.DataFrame(text_data, columns=['Extracted Text'])
    # Write the DataFrame to an Excel file
    df.to_excel(excel_file_path, index=False, engine='openpyxl')
    print("Text extraction complete. Check the output file located at:", excel_file_path)
else:
    print("No text was extracted from any PDF files.")
