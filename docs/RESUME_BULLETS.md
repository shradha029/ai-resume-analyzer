# Resume / interview notes

Fill the <...> values ONLY with numbers from your own runs (`role_classifier_metrics.json`, `pytest`, `npm test`). Do not claim anything you did not measure.

## Resume bullets (ATS-friendly)
- Built an AI-powered resume analyzer and skill-gap detection system (React, FastAPI, SQLAlchemy, scikit-learn) that parses PDF resumes, matches them to job descriptions and generates a PDF report.
- Designed an explainable weighted matching engine (TF-IDF cosine similarity, optional Sentence Transformers, skill-coverage scoring) and trained/compared Logistic Regression, Naive Bayes and Linear SVM job-role classifiers: <model> reached <macro-F1> macro-F1 on a held-out test set of <N> job descriptions (<dataset>).
- Implemented JWT authentication, validated file uploads, REST APIs and a Recharts analytics dashboard, backed by <N> backend and <N> frontend automated tests.

Project line: AI-Powered Resume Analyzer and Job-Specific Skill Gap Detection System | Python, FastAPI, React, scikit-learn, NLP, TF-IDF, SQLAlchemy, REST API, JWT

## Questions to be ready for
1. Why is the skill match not just keyword overlap? (credit levels: demonstrated / implied / listed / related; mandatory vs preferred weights)
2. How did you pick the classifier? (cross-validation on train, one final look at the test set)
3. Why can a score be "unknown"? (missing information is excluded, never counted as zero)
4. What are the limits? (rule-based parser, no OCR, dictionary-based skills, dataset-dependent classifier, not a hiring probability)
5. What would you improve? (spaCy NER, OCR, PostgreSQL + Alembic, calibrated semantic threshold, larger labelled data)
