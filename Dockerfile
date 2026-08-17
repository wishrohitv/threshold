FROM python:3.11-slim

WORKDIR /src

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=3000

EXPOSE 3000

CMD [ "gunicorn", "--chdir", "src", "-w", "2", "-b", "0.0.0.0:3000", "--capture-output", "--log-level", "info", "run:app" ]