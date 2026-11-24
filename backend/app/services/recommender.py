"""Rule-based, gap-driven recommendations. Every recommendation is tied to a detected gap or a failed
quality rule. Nothing is invented about the candidate: advice says "only if you have actually done it".
"""

# skill -> (what to do, project idea)
SKILL_PLAYBOOK = {
    "Docker": ("Learn Docker fundamentals (images, containers, volumes).", "Containerize one of your existing projects: write a Dockerfile and a docker-compose.yml."),
    "Kubernetes": ("Learn Kubernetes basics (pods, deployments, services).", "Deploy a containerized project to a local cluster (minikube or kind)."),
    "AWS": ("Get practical cloud experience on AWS (free tier).", "Deploy one project to AWS (for example EC2 or Elastic Beanstalk) and document the steps in the README."),
    "Azure": ("Learn core Azure services.", "Deploy a small web app to Azure App Service."),
    "GCP": ("Learn core Google Cloud services.", "Deploy a small service to Cloud Run."),
    "JWT": ("Learn token-based authentication.", "Add JWT login/logout and protected routes to a project."),
    "REST API": ("Learn REST API design (resources, status codes, validation).", "Build a CRUD API with authentication and test it with Postman."),
    "SQL": ("Practise SQL queries (joins, aggregation, indexes).", "Design a small relational schema and write queries for a real use case."),
    "PostgreSQL": ("Learn PostgreSQL basics.", "Move one project's database to PostgreSQL."),
    "MySQL": ("Learn MySQL basics.", "Build a project with a MySQL schema and queries."),
    "MongoDB": ("Learn MongoDB document modelling.", "Build a small API backed by MongoDB."),
    "FastAPI": ("Learn FastAPI.", "Rebuild one of your APIs in FastAPI and open its auto-generated /docs page."),
    "Django": ("Learn Django (models, views, ORM).", "Build a small CRUD application with Django."),
    "Flask": ("Learn Flask.", "Build a small REST API with Flask."),
    "React": ("Learn React (components, hooks, state).", "Build a small dashboard that calls a real API."),
    "Node.js": ("Learn Node.js.", "Build a small API with Node.js and Express."),
    "Git": ("Learn Git workflows (branches, pull requests).", "Put your projects on GitHub with meaningful commits."),
    "CI/CD": ("Learn continuous integration basics.", "Add a GitHub Actions workflow that runs tests on every push."),
    "Machine Learning": ("Strengthen core ML skills.", "Train and evaluate a model on a public dataset and report accuracy, precision, recall and F1."),
    "Deep Learning": ("Learn deep learning basics.", "Train a small neural network with PyTorch or TensorFlow."),
    "NLP": ("Learn NLP basics.", "Build a text-classification project with TF-IDF and a classifier."),
    "Pandas": ("Learn data manipulation with Pandas.", "Clean and analyse a real dataset in a notebook."),
    "Data Structures and Algorithms": ("Practise DSA regularly.", "Solve problems on a coding platform and keep notes on patterns."),
    "TensorFlow": ("Learn TensorFlow/Keras.", "Train and evaluate a small model."),
    "PyTorch": ("Learn PyTorch.", "Train and evaluate a small model."),
    "Scikit-learn": ("Learn scikit-learn.", "Compare 2-3 models on one dataset with proper evaluation."),
    "Tableau": ("Learn Tableau.", "Build a dashboard from a public dataset."),
    "Power BI": ("Learn Power BI.", "Build a dashboard from a public dataset."),
}

# official documentation links
RESOURCES = {
    "Python": ("Python tutorial", "https://docs.python.org/3/tutorial/"),
    "FastAPI": ("FastAPI tutorial", "https://fastapi.tiangolo.com/tutorial/"),
    "Django": ("Django documentation", "https://docs.djangoproject.com/"),
    "Flask": ("Flask documentation", "https://flask.palletsprojects.com/"),
    "PostgreSQL": ("PostgreSQL documentation", "https://www.postgresql.org/docs/"),
    "MySQL": ("MySQL documentation", "https://dev.mysql.com/doc/"),
    "MongoDB": ("MongoDB documentation", "https://www.mongodb.com/docs/"),
    "Docker": ("Docker get started", "https://docs.docker.com/get-started/"),
    "Kubernetes": ("Kubernetes tutorials", "https://kubernetes.io/docs/tutorials/"),
    "AWS": ("AWS documentation", "https://docs.aws.amazon.com/"),
    "Azure": ("Microsoft Learn: Azure", "https://learn.microsoft.com/azure/"),
    "GCP": ("Google Cloud documentation", "https://cloud.google.com/docs"),
    "React": ("React learn", "https://react.dev/learn"),
    "Node.js": ("Node.js documentation", "https://nodejs.org/docs/latest/api/"),
    "Express.js": ("Express documentation", "https://expressjs.com/"),
    "Git": ("Git documentation", "https://git-scm.com/doc"),
    "CI/CD": ("GitHub Actions documentation", "https://docs.github.com/actions"),
    "JWT": ("Introduction to JWT", "https://jwt.io/introduction"),
    "Scikit-learn": ("scikit-learn user guide", "https://scikit-learn.org/stable/user_guide.html"),
    "TensorFlow": ("TensorFlow tutorials", "https://www.tensorflow.org/tutorials"),
    "PyTorch": ("PyTorch tutorials", "https://pytorch.org/tutorials/"),
    "Pandas": ("Pandas getting started", "https://pandas.pydata.org/docs/getting_started/"),
    "NumPy": ("NumPy learn", "https://numpy.org/learn/"),
    "SQL": ("PostgreSQL tutorial (SQL basics)", "https://www.postgresql.org/docs/current/tutorial.html"),
    "JavaScript": ("MDN JavaScript guide", "https://developer.mozilla.org/docs/Web/JavaScript/Guide"),
    "HTML": ("MDN HTML", "https://developer.mozilla.org/docs/Web/HTML"),
    "CSS": ("MDN CSS", "https://developer.mozilla.org/docs/Web/CSS"),
}

CERT_HINTS = {
    "AWS": "AWS Certified Cloud Practitioner",
    "Azure": "Microsoft Azure Fundamentals (AZ-900)",
    "GCP": "Google Cloud Digital Leader",
    "Kubernetes": "Kubernetes and Cloud Native Associate (KCNA)",
}
_PRIO = {"high": 0, "medium": 1, "low": 2}


def _res(skill):
    r = RESOURCES.get(skill)
    return [{"name": r[0], "url": r[1]}] if r else []


def _rec(category, priority, title, action, reason, resources=None):
    return {"category": category, "priority": priority, "title": title, "action": action,
            "reason": reason, "resources": resources or []}


def build_recommendations(result: dict, quality: dict, job: dict, max_items: int = 18) -> list[dict]:
    recs = []
    matches = result["skill_matches"]
    prio = {"mandatory": "high", "preferred": "medium", "optional": "low"}

    for m in matches:
        s, lvl = m["skill"], m["level"]
        play = SKILL_PLAYBOOK.get(s)
        if m["status"] == "missing":
            what, project = play if play else (
                f"Study {s} fundamentals from its official documentation.", f"Use {s} in a small project and publish it on GitHub.")
            recs.append(_rec("skill", prio[lvl], f"Learn {s}", f"{what} {project}",
                             f"{lvl.capitalize()} requirement '{s}' was not found in your resume.", _res(s)))
        elif m["status"] == "partial" and m["evidence"] and m["evidence"][0].startswith("related"):
            have = m["evidence"][0].split(":", 1)[1].strip()
            recs.append(_rec("skill", prio[lvl] if lvl != "mandatory" else "medium", f"Bridge from {have} to {s}",
                             f"You already know {have}. Learn {s} and rebuild one small project with it to show direct experience.",
                             f"'{s}' is {lvl} for this job; your resume shows only the related skill(s) {have}.", _res(s)))
        elif m["status"] == "partial" and m["evidence"] == ["skills"]:
            recs.append(_rec("evidence", "medium" if lvl == "mandatory" else "low", f"Show real use of {s}",
                             f"Add a project or experience bullet describing what you built with {s}. "
                             f"If you have not used it in a project yet, build a small one first - do not claim experience you do not have.",
                             f"'{s}' is only listed in your Skills section, with no project or experience showing it."))

    for g in result["gaps"]:
        t = g["gap_type"]
        if t == "experience":
            recs.append(_rec("experience", g["severity"], "Build practical experience",
                             "Apply for internships or open-source/freelance tasks, or build 1-2 projects that mimic real work "
                             "(Git workflow, tests, deployment, README). Add them to your resume once completed.",
                             g["description"]))
        elif t == "qualification":
            recs.append(_rec("education", "medium", "Address the education requirement",
                             "Check whether your degree and field meet the stated requirement. If a different level is expected, "
                             "highlight relevant coursework, projects or certifications that cover the gap.", g["description"]))
        elif t == "certification":
            missing_cloud = [s for s in CERT_HINTS if any(m["skill"] == s for m in matches)]
            hint = (" Examples related to this job: " + ", ".join(CERT_HINTS[s] for s in missing_cloud) + ".") if missing_cloud else ""
            recs.append(_rec("certification", "low", "Add a relevant certification",
                             "Complete a recognised course or certification related to the job's core skills and list it with issuer and year." + hint,
                             g["description"]))
        elif t == "project_relevance":
            top = [m["skill"] for m in matches if m["level"] == "mandatory" and not m["demonstrated"]][:4]
            recs.append(_rec("project", "medium", "Build a project aligned with this job",
                             "Create or rework a project that uses the job's key skills" + (f" (especially {', '.join(top)})" if top else "") +
                             ", with 2-3 bullets explaining what you built.", g["description"]))

    for comp in quality["components"].values():
        for r in comp["rules"]:
            if r["advice"] and r["points"] < r["max"] * 0.75:
                recs.append(_rec("resume_quality", "medium" if comp["max"] >= 15 else "low", f"Resume: {r['rule']}",
                                 r["advice"], f"Quality rule scored {r['points']}/{r['max']}: {r['detail']}."))

    seen, out = set(), []
    for r in sorted(recs, key=lambda r: _PRIO[r["priority"]]):
        key = (r["category"], r["title"])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out[:max_items]
