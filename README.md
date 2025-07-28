📄 Adobe India Hackathon 2025 – Challenge 1A


🧠 PDF Outline Extraction Engine


Welcome to our submission for Round 1A of the Adobe "Connecting the Dots" Hackathon 2025. This solution focuses on making raw PDFs machine-readable by extracting their logical outline structure—Title, and hierarchical headings (H1, H2, H3), with page numbers.

✅ Objective
Build a system that:

Accepts a PDF file (≤ 50 pages)

Extracts:

📌 Title

🔖 Headings: H1, H2, H3 (along with page numbers)

Outputs structured data in valid JSON format

🗂 Folder Structure

Adobe-Challenge-main/

├── Dockerfile              # Docker configuration file

├── .dockerignore           # Files to ignore in Docker context

├── requirements.txt        # Python dependencies

├── app.py                 # Script for Challenge 1A (automatic PDF processing)

├── venv/                   # Local virtual environment (ignored)

⚙️ Expected Execution (Automatic Mode via Docker)


🔨 Build the Docker Image


docker build --platform linux/amd64 -t adobe-outline-extractor .


🚀 Run the Docker Container

docker run --rm -p 8501:8501 adobe-outline-extractor
