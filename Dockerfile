FROM python:3.10

WORKDIR /app/src
COPY . /app/src
RUN pip install -r requirements.txt

CMD python main.py