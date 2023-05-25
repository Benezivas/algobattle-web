FROM node as builder

ADD . .
RUN npm ci
RUN npm run build

FROM codecentric/single-page-application-server
COPY --from=builder /dist /app
ADD ./config.yaml /config/config.yaml
