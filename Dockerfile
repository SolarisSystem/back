FROM alpine:3.20

RUN apk update
RUN apk add python3 py3-pip

RUN mkdir -p /src
WORKDIR /src
COPY . /src

RUN pip3 install --break-system-packages -r requirements.txt

CMD python3 solaris/app.py
