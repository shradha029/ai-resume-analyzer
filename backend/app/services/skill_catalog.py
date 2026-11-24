"""Skill dictionary used for resume parsing (and reused for job descriptions in Phase 3).

Each entry: (canonical name, category, extra aliases, section-only aliases).
- aliases are matched case-insensitively anywhere in the text.
- section-only aliases are case-sensitive and counted only inside a Skills section
  (for ambiguous words such as "C", "R", "Go", "Express").
"""
import re

SKILLS: list[tuple[str, str, list[str], list[str]]] = [
    # languages
    ("Python", "language", ["python3"], []),
    ("C++", "language", ["cpp"], []),
    ("C", "language", [], ["C"]),
    ("Java", "language", [], []),
    ("JavaScript", "language", ["ecmascript", "es6"], []),
    ("TypeScript", "language", [], []),
    ("C#", "language", ["csharp"], []),
    ("Go", "language", ["golang"], ["Go"]),
    ("Rust", "language", [], []),
    ("PHP", "language", [], []),
    ("Kotlin", "language", [], []),
    ("Swift", "language", [], []),
    ("Ruby", "language", [], []),
    ("R", "language", [], ["R"]),
    ("SQL", "language", [], []),
    ("HTML", "language", ["html5"], []),
    ("CSS", "language", ["css3"], []),
    ("Bash", "language", ["shell scripting", "shell"], []),
    ("MATLAB", "language", [], []),
    ("Scala", "language", [], []),
    ("Dart", "language", [], []),
    # frameworks
    ("React", "framework", ["react.js", "reactjs", "react js"], []),
    ("React Native", "framework", [], []),
    ("Next.js", "framework", ["nextjs"], []),
    ("Angular", "framework", ["angularjs"], []),
    ("Vue.js", "framework", ["vue", "vuejs"], []),
    ("Node.js", "framework", ["nodejs", "node js"], ["Node"]),
    ("Express.js", "framework", ["expressjs", "express js"], ["Express"]),
    ("Django", "framework", [], []),
    ("Flask", "framework", [], []),
    ("FastAPI", "framework", ["fast api"], []),
    ("Spring Boot", "framework", ["springboot"], []),
    ("Tailwind CSS", "framework", ["tailwind", "tailwindcss"], []),
    ("Bootstrap", "framework", [], []),
    (".NET", "framework", ["dotnet", "asp.net"], []),
    ("Laravel", "framework", [], []),
    ("Redux", "framework", [], []),
    ("Flutter", "framework", [], []),
    ("Streamlit", "framework", [], []),
    # libraries
    ("NumPy", "library", [], []),
    ("Pandas", "library", [], []),
    ("Scikit-learn", "library", ["scikit learn", "sklearn", "scikitlearn"], []),
    ("TensorFlow", "library", [], []),
    ("PyTorch", "library", [], []),
    ("Keras", "library", [], []),
    ("OpenCV", "library", ["cv2"], []),
    ("spaCy", "library", [], []),
    ("NLTK", "library", [], []),
    ("Matplotlib", "library", [], []),
    ("Seaborn", "library", [], []),
    ("Hugging Face", "library", ["huggingface"], []),
    ("Sentence Transformers", "library", ["sentence-transformers", "sbert"], []),
    ("Plotly", "library", [], []),
    ("SciPy", "library", [], []),
    ("XGBoost", "library", [], []),
    ("LangChain", "library", [], []),
    ("Axios", "library", [], []),
    ("jQuery", "library", [], []),
    ("Recharts", "library", [], []),
    ("SQLAlchemy", "library", [], []),
    # databases
    ("MySQL", "database", [], []),
    ("PostgreSQL", "database", ["postgres"], []),
    ("MongoDB", "database", ["mongo db", "mongo"], []),
    ("SQLite", "database", [], []),
    ("Redis", "database", [], []),
    ("Oracle", "database", [], []),
    ("Firebase", "database", [], []),
    ("SQL Server", "database", ["mssql"], []),
    ("DynamoDB", "database", [], []),
    # tools
    ("Git", "tool", [], []),
    ("GitHub", "tool", [], []),
    ("Docker", "tool", [], []),
    ("Kubernetes", "tool", ["k8s"], []),
    ("Jenkins", "tool", [], []),
    ("Postman", "tool", [], []),
    ("Linux", "tool", [], []),
    ("VS Code", "tool", ["vscode", "visual studio code"], []),
    ("Jira", "tool", [], []),
    ("Jupyter", "tool", ["jupyter notebook", "jupyter notebooks"], []),
    ("Google Colab", "tool", ["colab"], []),
    ("Figma", "tool", [], []),
    ("Tableau", "tool", [], []),
    ("Power BI", "tool", ["powerbi"], []),
    ("Excel", "tool", ["ms excel", "microsoft excel"], []),
    ("CI/CD", "tool", ["ci cd", "cicd", "continuous integration"], []),
    ("Vite", "tool", [], []),
    ("Webpack", "tool", [], []),
    ("npm", "tool", [], []),
    ("Swagger", "tool", ["openapi"], []),
    # cloud
    ("AWS", "cloud", ["amazon web services"], []),
    ("Azure", "cloud", ["microsoft azure"], []),
    ("GCP", "cloud", ["google cloud", "google cloud platform"], []),
    ("Heroku", "cloud", [], []),
    ("Vercel", "cloud", [], []),
    ("Netlify", "cloud", [], []),
    # machine learning
    ("Machine Learning", "ml", [], []),
    ("Deep Learning", "ml", [], []),
    ("NLP", "ml", ["natural language processing"], []),
    ("Computer Vision", "ml", [], []),
    ("Generative AI", "ml", ["genai", "llm", "llms", "large language models"], []),
    ("Data Analysis", "ml", ["data analytics"], []),
    ("Data Visualization", "ml", ["data visualisation"], []),
    ("Statistics", "ml", [], []),
    # concepts
    ("REST API", "concept", ["rest apis", "restful api", "restful apis", "restful", "rest services", "restful services"], []),
    ("Data Structures and Algorithms", "concept", ["dsa", "data structures & algorithms", "data structures"], []),
    ("OOP", "concept", ["oops", "object oriented programming", "object-oriented programming", "object oriented"], []),
    ("DBMS", "concept", ["database management systems", "database management system"], []),
    ("Operating Systems", "concept", [], []),
    ("Computer Networks", "concept", [], []),
    ("Microservices", "concept", ["microservice"], []),
    ("JWT", "concept", ["json web token", "json web tokens"], []),
    ("Agile", "concept", ["scrum"], []),
    ("Web Development", "concept", [], []),
]

_AMBIGUOUS = {"C", "R", "Go"}
_L = r"(?<![A-Za-z0-9+#.])"
_R = r"(?![A-Za-z0-9+#])"


def _compile():
    compiled = []
    for name, cat, aliases, strict in SKILLS:
        words = {a.lower() for a in aliases}
        if name not in _AMBIGUOUS:
            words.add(name.lower())
        rx = None
        if words:
            alt = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
            rx = re.compile(f"{_L}(?:{alt}){_R}", re.I)
        srx = None
        if strict:
            alt = "|".join(re.escape(w) for w in sorted(strict, key=len, reverse=True))
            srx = re.compile(f"{_L}(?:{alt}){_R}")
        compiled.append((name, cat, rx, srx))
    return compiled


_COMPILED = _compile()


def find_skills(text: str, skills_section: bool = False) -> dict[str, str]:
    """Return {canonical skill: category} found in text."""
    found: dict[str, str] = {}
    for name, cat, rx, srx in _COMPILED:
        if (rx and rx.search(text)) or (skills_section and srx and srx.search(text)):
            found[name] = cat
    return found
