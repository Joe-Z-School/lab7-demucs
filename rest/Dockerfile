FROM python:3.6-alpine

WORKDIR /srv

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY rest-server.py /srv

EXPOSE 5000

CMD [ "python3", "rest-server.py" ]