FROM python:3.12.3

ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
EXPOSE 8000

RUN mkdir database

RUN python manage.py migrate
CMD python3 manage.py runserver 0.0.0.0:8000