FROM python:3.11 as api_builder
WORKDIR /code
COPY backend .
RUN pip install .
COPY config.toml .
ENV ALGOBATTLE_CONFIG_PATH=config.toml
RUN algobattle_api > openapi.json

FROM openapitools/openapi-generator-cli as ts_builder
WORKDIR /code
COPY --from=api_builder /code/openapi.json openapi.json
RUN /usr/local/bin/docker-entrypoint.sh generate -g typescript-fetch -i openapi.json -o typescript_client

FROM node as frontend_builder
WORKDIR /code
COPY --from=ts_builder /code/typescript_client typescript_client
COPY frontend .
RUN npm ci
RUN npm run build

FROM nginx
WORKDIR /code
COPY --from=frontend_builder /code/dist frontend
