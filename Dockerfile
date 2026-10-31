# NutriAgent AI - the Streamlit web app (app.py).
# Build:  docker build -t nutriagent .
# Run:    docker run -d --name nutriagent --network host --restart unless-stopped nutriagent
# Then open http://<server-ip>:8501
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 STREAMLIT_SERVER_ADDRESS=0.0.0.0 STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py agents.py extractor.py deterministic_nutrition.py general_intake.py indian_foods.py nin_food_data.json sample_blood_test_report.pdf ./

RUN useradd -m -u 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).status==200 else 1)"

CMD ["streamlit", "run", "app.py"]
