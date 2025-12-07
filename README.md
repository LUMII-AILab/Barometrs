# Setup for development build within Docker containers
1. Create `.env` file according to `.env.example`.
2. Run `docker-compose -f docker-compose.dev.yml up --build -d` to build and start development containers.
3. (optional) [Pycharm] Set up remote interpreter (not recommended, use local interpreter instead):
   - Go to `File -> Settings -> Project -> Python Interpreter`.
   - Click `Add interpreter -> On SSH...`.
   - Fill in the fields (double-check the values in `docker-compose.dev.yml`):
     - Host: `localhost`.
     - Port: `2222`.
     - Username: `root`.
     - Password: no password.
     - Use System installed interpreter: `selected`.
     - Automatically sync project files: `checked`.
     - Path mappings: `<Project root> → /app`
   - Click `OK`.
   - Local project files might get [wiped out](https://youtrack.jetbrains.com/issue/WI-5900/problem-with-automatic-upload-local-deletions-are-applied-to-server), just don't commit them and unstage changes.
   - To connect to SSH via terminal run `ssh root@localhost -p 2222`.
4. Create volume for language models:
   ```
   docker volume create barometrs-language_models_volume
   ```
5. Run `download_models.py` to download language models from HuggingFace inside `web` container:
   ```
   docker exec -it web bash -c "python3 /app/download_models.py"
   ```
6. Credentials to connect to PostgreSQL are in `.env` file.
7. Run `init_db.py` to create tables:
   ```
   docker exec -it web bash -c "python3 /app/init_db.py"
   ```
8. Extract the raw data (comments) inside `data` folder. See the expected paths per news outlet inside `core/data_import.py`
<br> As of now, the following folders are expected:
   - Delfi - `data/delfi/`
   - Delfi-new - `data/delfi-new/`
   - Apollo - `data/apollo/`
   - TVNET - `data/tvnet/`
9. Run `data_import.py` to import articles and comments into the database:
   ```
   docker exec -it -w /app web python3 -m core.data_import
   ```
10. Run `predict_comments.py` to predict emotions for the imported comments:
   ```
   docker exec -it -w /app web python3 -m core.predict_comments
   ```
11. Run `extract_keywords_by_day.py` to extract keywords:
   ```
   docker exec -it -w /app web python3 -m core.extract_keywords_by_day
   ```

# Database export
Create database dump in plain-text format:
```
docker exec db pg_dump -U barometrs -d barometrs -f /tmp/barometrs.sql
docker cp db:/tmp/barometrs.sql ./barometrs.sql
```

Create database dump in directory-format:
```
docker exec barometrs-db pg_dump -U emotion_classification -d emotion_classification -Fc -Z 9 -f /tmp/emotion_classification.dump
docker cp barometrs-db:/tmp/emotion_classification.dump ./emotion_classification.dump
```

# Database import
1. Wipe out database:
```
docker exec -u root barometrs-db bash -c "rm -rf /var/lib/postgresql/data/*"
```
2. Copy data:
```
docker cp path_to/var/lib/postgresql/data/. barometrs-db:/var/lib/postgresql/data
```