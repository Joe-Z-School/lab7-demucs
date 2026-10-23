FROM python:3.11

WORKDIR /srv

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY worker.py /srv

CMD [ "python3", "worker.py" ]