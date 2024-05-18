import os

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def base_path(subpath=''):
    return os.path.join(BASE_DIR, subpath)

def data_path(subpath=''):
    return os.path.join(BASE_DIR, 'data', subpath)

def models_path(subpath=''):
    return os.path.join(BASE_DIR, 'models', subpath)

def stopwords_path(subpath=''):
    return os.path.join(BASE_DIR, 'stopwords', subpath)