FROM python:3.11 as api_builder
WORKDIR /code
COPY backend .
RUN pip install .
COPY config.toml /algobattle/config.toml
RUN algobattle_api > openapi.json
RUN pip show algobattle_base | grep -oP "Version: \K[^\n]+" > algobattle_version.txt

FROM node as frontend_builder
WORKDIR /code
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY --from=api_builder /code/openapi.json openapi.json
RUN npx openapi --input ./openapi.json --output ./typescript_client --useOptions
COPY frontend .
RUN npm run build

FROM nginx
WORKDIR /code
COPY --from=api_builder /code/algobattle_version.txt algobattle_version.txt
RUN curl -OL https://github.com/ImogenBits/algobattle/releases/download/v`cat algobattle_version.txt`/docs.tar.gz
RUN mkdir docs && tar xzf docs.tar.gz -C docs
COPY --from=frontend_builder /code/dist frontend
