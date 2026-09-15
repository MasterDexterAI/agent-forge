# image agents actually run code inside

FROM python:3.11-slim
RUN useradd -m sandboxuser
USER sandboxuser
WORKDIR /workspace