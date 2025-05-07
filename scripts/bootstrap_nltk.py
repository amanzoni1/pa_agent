# scripts/bootstrap_nltk.py
import nltk, logging, os, certifi, ssl

os.environ["SSL_CERT_FILE"] = certifi.where()
ssl._create_default_https_context = ssl.create_default_context

for pkg in ("punkt", "punkt_tab", "averaged_perceptron_tagger_eng"):
    try:
        (
            nltk.data.find(f"tokenizers/{pkg}")
            if "punkt" in pkg
            else nltk.data.find(f"taggers/{pkg}/")
        )
    except LookupError:
        logging.info("Downloading %s …", pkg)
        nltk.download(pkg, quiet=True)

logging.info("✔ NLTK bootstrap complete")
