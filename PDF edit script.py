# -*- coding: utf-8 -*-
"""
Created on Wed Apr  9 17:27:46 2025

@author: rahul_borse
"""
import PyPDF2

# Specify the path to your PDF file
pdf_file_path = 'C:/Users/rahul_borse/Python/Files(35).pdf'  
text_file_path = 'C:/Users/rahul_borse/Python/output.xlsx'  ##

# Open the PDF file
try:
    with open(pdf_file_path, 'rb') as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        
        # Create or open a text file to write the extracted text
        with open(text_file_path, 'w', encoding='utf-8') as text_file:
            # Iterate through each page of the PDF
            for page in reader.pages:
                text = page.extract_text()  # Extract text from the page
                if text:  # Check if text was extracted
                    text_file.write(text + '\n')  # Write the text to the text file

    print("Text extraction complete. Check the output file.")

except PermissionError:
    print("Permission denied. Please check the file path and permissions.")
except FileNotFoundError:
    print("The specified PDF file was not found. Please check the file path.")
except Exception as e:
    print(f"An error occurred: {e}")
