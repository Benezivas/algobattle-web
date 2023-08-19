FROM python:3.11 as api_builder
WORKDIR /code
COPY backend .
RUN pip install .
COPY config.toml /algobattle/config.toml
RUN algobattle_api > openapi.json

FROM node as frontend_builder
WORKDIR /code
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY --from=api_builder /code/openapi.json openapi.json
RUN npx openapi --input ./openapi.json --output ./typescript_client --useOptions
COPY frontend .
RUN npm run build

FROM python:3.11 as docs_builder
WORKDIR /code
RUN git clone -b "4.0.0-rc" https://github.com/ImogenBits/algobattle.git
WORKDIR /code/algobattle
RUN pip install .[dev]
RUN mkdocs build

FROM nginx
WORKDIR /code
COPY --from=frontend_builder /code/dist frontend
COPY --from=docs_builder /code/algobattle/site docs
