FROM python:3.9

ADD *.py .

pip install -r requirements.txt

CMD [“python”, “./luxmedbot.py”] 
