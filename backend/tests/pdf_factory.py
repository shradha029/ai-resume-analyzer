"""Helpers that build synthetic PDFs (used by tests and the sample generator)."""
import pymupdf


def make_pdf(text: str, font_size: int = 10, line_height: int = 14) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 50
    for line in text.split("\n"):
        if y > 780:
            page, y = doc.new_page(), 50
        if line.strip():
            page.insert_text((50, y), line, fontsize=font_size)
        y += line_height
    data = doc.tobytes()
    doc.close()
    return data


def blank_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


def image_only_pdf() -> bytes:
    """A page that contains only an image (like a scanned resume): no selectable text."""
    doc = pymupdf.open()
    page = doc.new_page()
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 120, 120))
    pix.clear_with(255)
    page.insert_image(page.rect, pixmap=pix)
    data = doc.tobytes()
    doc.close()
    return data


def encrypted_pdf(text: str = "Secret resume text that is long enough to count as content.") -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 50), text)
    data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner")
    doc.close()
    return data


STUDENT_RESUME = """AARAV SHARMA
aarav.sharma@example.com | +91 98765 43210
linkedin.com/in/aarav-sharma-demo | github.com/aaravsharma-demo
https://aarav-demo.dev
EDUCATION
B.Tech in Computer Science and Engineering
Example Institute of Technology, New Delhi
2021 - 2025
CGPA: 8.10/10
Relevant Coursework: Data Structures, DBMS, Operating Systems, Machine Learning
Senior Secondary (Class XII), Demo Public School
2021 | 92.4%
TECHNICAL SKILLS
Languages: Python, C++, Java, JavaScript, SQL
Frameworks: ReactJS, Node.js, Express, Flask
Libraries: NumPy, Pandas, scikit learn
Databases: MySQL, MongoDB
Tools: Git, GitHub, Docker, Postman
PROJECTS
Smart Attendance System | Python, OpenCV, Flask
• Built a face-recognition attendance app that processes 50 images per minute
• Stored records in MySQL and exposed RESTful APIs for a React dashboard
Movie Recommender
• Created a content-based recommender using TF-IDF and cosine similarity
• Deployed on Heroku
CERTIFICATIONS
Machine Learning Specialization - Coursera (2023)
Python for Everybody - University of Michigan, 2022
ACHIEVEMENTS
• Finalist, Example University Hackathon 2024
• Solved 300+ DSA problems on coding platforms
"""

INTERN_RESUME = STUDENT_RESUME.replace(
    "CERTIFICATIONS",
    """INTERNSHIPS
Software Development Intern | Demo Tech Pvt. Ltd.   Jun 2024 - Aug 2024
• Developed REST APIs using FastAPI and PostgreSQL
• Reduced API response time by 30% through query optimisation
CERTIFICATIONS""",
)
