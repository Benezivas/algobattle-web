FROM python:3.11 as api_builder
WORKDIR /code
COPY backend .
RUN pip install .
ARG ALGOBATTLE_DB_PW
ARG ALGOBATTLE_BASE_URL
ENV ALGOBATTLE_DB_PW=${ALGOBATTLE_DB_PW} ALGOBATTLE_BASE_URL=${ALGOBATTLE_BASE_URL}
RUN algobattle_api > openapi.json
RUN pip show algobattle_base | grep -oP "Version: \K[^\n]+" > algobattle_version.txt

FROM node:20 as frontend_builder
WORKDIR /code
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/env.d.ts frontend/index.html frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts ./
COPY --from=api_builder /code/openapi.json openapi.json
RUN npx openapi-typescript-codegen --input ./openapi.json --output ./typescript_client --useOptions --useUnionTypes
COPY frontend/public public/
COPY frontend/src src/
RUN npm run build

FROM nginx
WORKDIR /code
COPY --from=api_builder /code/algobattle_version.txt algobattle_version.txt
RUN curl -OL https://github.com/Benezivas/algobattle/releases/download/v`cat algobattle_version.txt`/docs.tar.gz
RUN mkdir docs && tar xzf docs.tar.gz -C docs
COPY --from=frontend_builder /code/dist frontend
