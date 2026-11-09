"""Check import and an actual tiny CPU fit in the selected Python environment."""
import json
import os
import sys
from pathlib import Path

handles = []
if os.name == "nt":
    for directory in (Path(sys.base_prefix) / "Library" / "bin", Path(sys.base_prefix) / "DLLs"):
        if directory.is_dir():
            handles.append(os.add_dll_directory(str(directory)))
            os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", "")
import joblib
import numpy
import scipy
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

matrix = TfidfVectorizer().fit_transform(["alpha one", "alpha two", "beta one", "beta two"])
LogisticRegression().fit(matrix, [0, 0, 1, 1])
print(json.dumps({"python":sys.version.split()[0], "sklearn":sklearn.__version__, "numpy":numpy.__version__,
                  "scipy":scipy.__version__, "joblib":joblib.__version__, "cpu_fit":True}))
