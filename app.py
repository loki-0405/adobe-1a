import streamlit as st
import json
import fitz  # PyMuPDF
import time
import re
from io import BytesIO

# ----------------- PDF Text Extraction Functions ----------------- #
def extract_text_from_pdf(pdf_file):
    pdf_doc = fitz.open(stream=pdf_file, filetype="pdf")
    extracted_content = []
    max_pages = min(len(pdf_doc), 50)
    for current_page in range(max_pages):
        page_blocks = pdf_doc[current_page].get_text("dict")["blocks"]
        for block in page_blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for text_span in line["spans"]:
                    clean_text = text_span["text"].strip()
                    if not clean_text or len(clean_text) <= 1:
                        continue
                    extracted_content.append({
                        "text": clean_text,
                        "size": text_span["size"],
                        "font": text_span["font"],
                        "flags": text_span.get("flags", 0),
                        "page": current_page + 1,
                        "bbox": text_span["bbox"]
                    })
    pdf_doc.close()
    return extracted_content

def analyze_document_structure(text_elements):
    """Identifies titles and headings in the document"""
    if not text_elements:
        return [], "No Title Found"

    all_sizes = [item["size"] for item in text_elements]
    average_size = sum(all_sizes) / len(all_sizes)
    unique_font_sizes = sorted(set(all_sizes), reverse=True)

    def clean_text(text_string):
        return re.sub(r'\s+', ' ', text_string.strip())

    def could_be_title(text_item, size, page_num, flags_value):
        if page_num > 2:
            return False
        if size < max(all_sizes) * 0.9:
            return False
        word_count = len(text_item.split())
        if word_count < 3 or word_count > 25:
            return False
        if re.match(r'^\d+\.?\s', text_item):
            return False
        if text_item.lower().startswith(('page', 'chapter')):
            return False
        return True

    def looks_like_heading(text_item, size, page_num, flags_value):
        normalized_text = clean_text(text_item)
        if len(normalized_text) < 2 or len(normalized_text) > 150:
            return False
        word_count = len(normalized_text.split())
        if word_count > 20:
            return False
        non_heading_patterns = [
            r'^\d+$', r'^page\s+\d+', r'^figure\s+\d+', 
            r'^table\s+\d+', r'^\w{1,2}$', r'^[^\w\s]+$',
            r'^\d{4}$', r'^www\.', r'@'
        ]
        if any(re.match(p, normalized_text.lower()) for p in non_heading_patterns):
            return False
        is_bold = bool(flags_value & 16)
        larger_than_normal = size > average_size * 1.15
        heading_patterns = [
            r'^\d+\.?\s+[A-Z]', r'^\d+\.\d+\.?\s+[A-Z]',
            r'^\d+\.\d+\.\d+\.?\s+[A-Z]', r'^\d+\.\d+\.\d+\.\d+\.?\s+[A-Z]',
            r'^[A-Z][a-z]+(\s+[A-Z&][a-z]*)*:?\s*$', r'^[A-Z][A-Z\s&]+:?\s*$',
            r'^Appendix\s+[A-Z]', r'^Phase\s+[IVX]',
            r'^For\s+(each|the)\s+[A-Z]', r'^\d+\.\s+[A-Z]'
        ]
        matches_pattern = any(re.match(p, normalized_text) for p in heading_patterns)
        common_heading_words = [
            'summary', 'background', 'introduction', 'conclusion',
            'abstract', 'references', 'methodology', 'approach',
            'requirements', 'evaluation', 'timeline', 'milestones',
            'appendix', 'phase', 'business', 'plan'
        ]
        contains_keyword = any(w in normalized_text.lower() for w in common_heading_words)
        ends_with_colon = normalized_text.endswith(':')
        heading_score = 0
        if is_bold: heading_score += 2
        if matches_pattern: heading_score += 3
        if larger_than_normal: heading_score += 1
        if contains_keyword: heading_score += 2
        if ends_with_colon: heading_score += 1
        if size >= average_size * 1.3: heading_score += 1
        return heading_score >= 4

    def determine_heading_level(text_item, size, page_num):
        clean_text_line = re.sub(r'\s+', ' ', text_item.strip())
        if re.match(r'^\d+\.?\s+[A-Z]', clean_text_line):
            return "H1"
        elif re.match(r'^\d+\.\d+\.?\s+', clean_text_line):
            return "H2"
        elif re.match(r'^\d+\.\d+\.\d+\.?\s+', clean_text_line):
            return "H3"
        elif re.match(r'^\d+\.\d+\.\d+\.\d+\.?\s+', clean_text_line):
            return "H4"
        if re.match(r'^Appendix\s+[A-Z]:', clean_text_line):
            return "H2"
        elif re.match(r'^Phase\s+[IVX]+:', clean_text_line):
            return "H3"
        elif re.match(r'^For\s+(each|the)\s+[A-Z]', clean_text_line):
            return "H4"
        elif re.match(r'^\d+\.\s+[A-Z]', clean_text_line):
            return "H3"
        if len(unique_font_sizes) >= 4:
            size_rank = unique_font_sizes.index(size) if size in unique_font_sizes else len(unique_font_sizes) - 1
            if size_rank == 0:
                return "H1"
            elif size_rank == 1:
                return "H2"
            elif size_rank == 2:
                return "H3"
            else:
                return "H4"
        else:
            if size >= average_size * 1.4:
                return "H1"
            elif size >= average_size * 1.25:
                return "H2"
            elif size >= average_size * 1.1:
                return "H3"
            else:
                return "H4"

    possible_titles = []
    for element in text_elements:
        if could_be_title(element["text"], element["size"], element["page"], element["flags"]):
            possible_titles.append({
                "text": clean_text(element["text"]),
                "size": element["size"],
                "page": element["page"]
            })
    doc_title = "Untitled Document"
    if possible_titles:
        best_candidate = max(possible_titles, key=lambda x: (x["size"] * 1000 - x["page"]))
        doc_title = best_candidate["text"]
    potential_headings = []
    processed_texts = set()
    for element in text_elements:
        text_cleaned = clean_text(element["text"])
        text_lower = text_cleaned.lower()
        if text_lower in processed_texts or text_lower == doc_title.lower():
            continue
        if looks_like_heading(element["text"], element["size"], element["page"], element["flags"]):
            heading_type = determine_heading_level(element["text"], element["size"], element["page"])
            potential_headings.append({
                "text": text_cleaned,
                "level": heading_type,
                "page": element["page"],
                "size": element["size"]
            })
            processed_texts.add(text_lower)
    potential_headings.sort(key=lambda x: (x["page"], -x["size"]))
    confirmed_headings = []
    for heading in potential_headings:
        text_content = heading["text"]
        if (len(text_content.split()) >= 2 and not re.match(r'^\d+$', text_content) and
                not text_content.lower() in ['page', 'figure', 'table'] and
                len(text_content.strip()) >= 3):
            confirmed_headings.append({
                "level": heading["level"],
                "text": text_content,
                "page": heading["page"]
            })
    return confirmed_headings, doc_title

# ------------------- Streamlit UI: Only the Structure Extraction Part ------------------- #
st.set_page_config(page_title="Document Analysis Tool – Structure Extraction", layout="wide")
st.title("PDF Document Analyzer: Document Structure")

st.subheader("PDF Structure Extraction")
uploaded_file = st.file_uploader("Choose PDF file", type=["pdf"], key="pdf-uploader")

if uploaded_file:
    st.write(f"**Selected file:** {uploaded_file.name}")
    if st.button("Analyze Document Structure"):
        progress = st.progress(0)
        for percent in range(101):
            time.sleep(0.01)
            progress.progress(percent)

        file_stream = BytesIO(uploaded_file.read())
        extracted_text = extract_text_from_pdf(file_stream)
        document_headings, main_title = analyze_document_structure(extracted_text)

        st.success("Analysis complete!")
        st.markdown(f"### Document Title: {main_title}")
        st.markdown("### Document Headings")
        for heading in document_headings:
            st.write(f"- **Page {heading['page']}** [{heading['level']}]: {heading['text']}")
        result_data = {
            "title": main_title,
            "outline": document_headings
        }
        st.markdown("### Analysis Results (JSON)")
        st.json(result_data)

        st.download_button(
            label="Download Results",
            data=json.dumps(result_data, indent=2),
            file_name="document_structure.json",
            mime="application/json"
        )
