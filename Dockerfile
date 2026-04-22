FROM ubuntu:latest
LABEL authors="georgio"

ENTRYPOINT ["top", "-b"]