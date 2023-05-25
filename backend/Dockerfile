FROM python:3.11

WORKDIR /code
COPY algobattle_web ./algobattle_web
COPY pyproject.toml ./pyproject.toml
RUN pip install .

CMD ["uvicorn", "algobattle_web.app:app", "--host", "0.0.0.0", "--port", "8000"]
