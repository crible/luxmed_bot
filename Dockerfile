FROM python:3.9

ADD *.py .
ADD requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 8443

CMD ["python", "./luxmedbot.py"] 
