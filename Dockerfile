FROM python:alpine3.7

RUN apk add build-base
RUN apk add openssl-dev
RUN apk add python3-dev

RUN pip install quart aiohttp hypercorn
COPY . /app
WORKDIR /app

CMD python3 -m hypercorn -b 0.0.0.0:5010 App:app