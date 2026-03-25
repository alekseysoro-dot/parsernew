FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

COPY scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build context = backend/ — copy both packages
COPY api/ ./api/
COPY scraper/ ./scraper/

CMD ["python", "-m", "scraper.scheduler"]
