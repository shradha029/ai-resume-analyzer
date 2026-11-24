"""Small SYNTHETIC dataset used only to test the training code. Never use it for reported accuracy."""
import random

import pandas as pd

POOLS = {
    "Data Science": "python pandas numpy scikit-learn machine learning model statistics regression classification dataset notebook visualization feature".split(),
    "Web Development": "react javascript html css frontend responsive component redux typescript browser ui webpack tailwind accessibility".split(),
    "DevOps": "docker kubernetes jenkins pipeline terraform aws deployment monitoring linux ansible infrastructure container ci cd uptime".split(),
    "Java Developer": "java spring hibernate maven junit microservices jvm servlet backend sql enterprise api tomcat".split(),
}
FILLER = "experience team work strong skills knowledge requirements candidate position company responsibilities".split()


def make_df(n_per_class: int = 60, seed: int = 0) -> pd.DataFrame:
    rnd = random.Random(seed)
    rows = []
    for label, pool in POOLS.items():
        for _ in range(n_per_class):
            words = rnd.choices(pool, k=18) + rnd.choices(FILLER, k=8)
            rnd.shuffle(words)
            rows.append({"text": "We are hiring. " + " ".join(words) + ". Apply today.", "label": label})
    return pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
