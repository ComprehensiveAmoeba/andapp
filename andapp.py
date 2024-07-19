import streamlit as st
from PyPDF2 import PdfWriter, PdfReader, PageObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import tempfile
import io
import requests
import os

# List of watermark URLs
watermark_urls = [
    "https://thrassvent.de/wp-content/uploads/2024/07/COPY-LOGO-1.png",
    "https://thrassvent.de/wp-content/uploads/2024/07/COPY-LOGO-2.png",
    "https://thrassvent.de/wp-content/uploads/2024/07/COPY-LOGO-3.png",
    "https://thrassvent.de/wp-content/uploads/2024/07/COPY-LOGO-4.png"
]

def add_watermark(input_pdf, watermark_source, transparency, style, scale, is_url=True):
    # Fetch or read the watermark image
    if is_url:
        response = requests.get(watermark_source)
        watermark_image = io.BytesIO(response.content)
    else:
        watermark_image = io.BytesIO(watermark_source.read())
    
    # Save watermark image to a temporary file
    temp_image_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    with open(temp_image_path, 'wb') as f:
        f.write(watermark_image.getbuffer())
    
    # Create a watermark PDF with the given image
    watermark_pdf = io.BytesIO()
    c = canvas.Canvas(watermark_pdf, pagesize=letter)
    c.setFillAlpha(transparency)  # Set transparency
    
    img = ImageReader(temp_image_path)
    img_width, img_height = img.getSize()
    aspect = img_height / float(img_width)
    width = scale * letter[0]  # Scale relative to the full width of the page
    height = aspect * width
    
    if style == 'mosaic':
        for y in range(0, int(letter[1]), int(height)):
            for x in range(0, int(letter[0]), int(width)):
                c.drawImage(temp_image_path, x, y, width=width, height=height)
    elif style == 'centered':
        c.drawImage(temp_image_path, (letter[0] - width) / 2, (letter[1] - height) / 2, width=width, height=height)
    
    c.save()
    watermark_pdf.seek(0)
    
    # Read the input PDF
    input_pdf = PdfReader(input_pdf)
    watermark_pdf = PdfReader(watermark_pdf)
    output_pdf = PdfWriter()
    
    # Add the watermark to each page
    for i in range(len(input_pdf.pages)):
        page = input_pdf.pages[i]
        page.merge_page(watermark_pdf.pages[0])
        output_pdf.add_page(page)
    
    # Write the watermarked PDF to a BytesIO object
    output_pdf_stream = io.BytesIO()
    output_pdf.write(output_pdf_stream)
    output_pdf_stream.seek(0)
    
    # Clean up the temporary image file
    os.remove(temp_image_path)
    
    return output_pdf_stream

def remove_bottom_pixels(input_pdf, height_to_remove, pages_to_modify):
    input_pdf = PdfReader(input_pdf)
    output_pdf = PdfWriter()

    for i, page in enumerate(input_pdf.pages):
        original_width = page.mediabox.upper_right[0]
        original_height = page.mediabox.upper_right[1]

        if i + 1 in pages_to_modify or not pages_to_modify:
            # Create a new blank canvas
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=(original_width, height_to_remove))
            
            # Fill the canvas with white color
            c.setFillColorRGB(1, 1, 1)
            c.rect(0, 0, original_width, height_to_remove, stroke=0, fill=1)
            c.save()
            packet.seek(0)
            
            # Create a new PDF with the blank area
            new_blank_page = PdfReader(packet).pages[0]
            
            # Merge the blank area with the original content
            new_page = PageObject.create_blank_page(width=original_width, height=original_height)
            new_page.merge_page(page)
            new_page.merge_page(new_blank_page, expand=False)
            
            output_pdf.add_page(new_page)
        else:
            output_pdf.add_page(page)
    
    output_pdf_stream = io.BytesIO()
    output_pdf.write(output_pdf_stream)
    output_pdf_stream.seek(0)
    
    return output_pdf_stream

def main():
    st.title("Andrea's PDF Tools")
    tab1, tab2 = st.tabs(["Merge and Watermark PDFs", "Merge and Trim PDFs"])

    with tab1:
        uploaded_files = st.file_uploader("Upload PDFs", accept_multiple_files=True, type="pdf", key="file_uploader_watermark")
        
        watermark_option = st.radio(
            "Select an option",
            ["Merge PDFs only", "Merge PDFs and add watermark"],
            key="watermark_option"
        )

        if watermark_option == "Merge PDFs and add watermark":
            watermark_source_option = st.radio(
                "Select a watermark source",
                ["Use preset logos", "Upload custom logo"],
                key="watermark_source_option"
            )

            if watermark_source_option == "Use preset logos":
                st.write("Select a watermark:")
                selected_watermark = st.radio(
                    "Watermarks",
                    watermark_urls,
                    format_func=lambda x: f"Watermark {watermark_urls.index(x) + 1}",
                    key="watermark_selection"
                )

                # Display the selected watermark preview
                if selected_watermark:
                    st.image(selected_watermark, caption=f"Selected Watermark {watermark_urls.index(selected_watermark) + 1}", use_column_width=False, width=150)

            else:
                uploaded_watermark = st.file_uploader("Upload a PNG watermark", type="png", key="custom_watermark")
                selected_watermark = uploaded_watermark

            style = st.selectbox("Watermark Style", ["mosaic", "centered"], key="watermark_style")
            
            st.write("**Transparency:** Recommended transparency is from 0.1 to 0.2.")
            transparency = st.slider("Transparency", 0.0, 0.5, 0.5, key="transparency")

            scale = st.slider("Scale (as a percentage of the page width)", 0.1, 1.0, 0.5, key="scale")

        if st.button("Merge PDFs", key="merge_button"):
            if uploaded_files:
                merged_pdf = PdfWriter()
                for uploaded_file in uploaded_files:
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        merged_pdf.add_page(page)

                temp_merged_pdf = tempfile.NamedTemporaryFile(delete=False)
                merged_pdf.write(temp_merged_pdf)
                temp_merged_pdf.close()

                if watermark_option == "Merge PDFs and add watermark" and selected_watermark:
                    is_url = watermark_source_option == "Use preset logos"
                    watermarked_pdf_stream = add_watermark(temp_merged_pdf.name, selected_watermark, transparency, style, scale, is_url)
                    output_pdf_stream = watermarked_pdf_stream
                else:
                    output_pdf_stream = io.BytesIO()
                    with open(temp_merged_pdf.name, 'rb') as f:
                        output_pdf_stream.write(f.read())
                    output_pdf_stream.seek(0)
                
                st.download_button(
                    label="Download Merged PDF" if watermark_option == "Merge PDFs only" else "Download Merged and Watermarked PDF",
                    data=output_pdf_stream,
                    file_name="merged.pdf" if watermark_option == "Merge PDFs only" else "merged_watermarked.pdf",
                    mime="application/pdf"
                )
    
    with tab2:
        uploaded_files = st.file_uploader("Upload PDFs", accept_multiple_files=True, type="pdf", key="file_uploader_trim")

        if uploaded_files:
            total_height = 0
            num_pages = 0
            for uploaded_file in uploaded_files:
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    total_height += page.mediabox.upper_right[1]
                    num_pages += 1
            if num_pages > 0:
                avg_height = total_height / num_pages
                st.write(f"Average Page Height: {avg_height:.2f} pixels")

        height_to_remove = st.number_input("Enter the height to remove from the bottom of the pages (in pixels):", min_value=0, key="height_to_remove")
        pages_to_modify = st.text_input("Enter comma-separated page numbers to modify (leave empty for all pages):", key="pages_to_modify")

        if st.button("Merge and Trim PDFs", key="trim_button"):
            if uploaded_files:
                if pages_to_modify:
                    pages_to_modify_list = [int(page.strip()) for page in pages_to_modify.split(",")]
                else:
                    pages_to_modify_list = list(range(1, num_pages + 1))

                merged_pdf = PdfWriter()
                for uploaded_file in uploaded_files:
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        merged_pdf.add_page(page)

                temp_merged_pdf = tempfile.NamedTemporaryFile(delete=False)
                merged_pdf.write(temp_merged_pdf)
                temp_merged_pdf.close()

                trimmed_pdf_stream = remove_bottom_pixels(temp_merged_pdf.name, height_to_remove, pages_to_modify_list)

                st.download_button(
                    label="Download Merged and Trimmed PDF",
                    data=trimmed_pdf_stream,
                    file_name="merged_trimmed.pdf",
                    mime="application/pdf"
                )

if __name__ == "__main__":
    main()
