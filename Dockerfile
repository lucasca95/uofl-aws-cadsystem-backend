FROM python:3.10-bullseye

WORKDIR /app

RUN pip install --upgrade pip
RUN apt update
RUN apt install -y build-essential libgl1-mesa-glx
RUN apt install -y ffmpeg libsm6 libxext6 libgl1

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN rm /bin/sh && ln -s /bin/bash /bin/sh

RUN useradd appuser && chown -R appuser /app
USER appuser

EXPOSE 8080

ENTRYPOINT ["python", "app.py"]

