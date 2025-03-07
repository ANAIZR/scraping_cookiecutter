FROM python:3.11-slim

RUN apt-get update && apt-get install -y wget gnupg unzip curl xvfb libxi6 libgconf-2-4 --no-install-recommends \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install selenium undetected-chromedriver flask

RUN python -c "import undetected_chromedriver as uc; uc.Chrome(headless=True).quit()"

COPY server.py /app/server.py

EXPOSE 4444

CMD ["python", "server.py"]
