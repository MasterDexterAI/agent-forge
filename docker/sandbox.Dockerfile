FROM python:3.12-slim
RUN pip install --no-cache-dir "pytest>=8,<9" && useradd -u 1000 -m sandboxuser
USER 1000
WORKDIR /workspace

# image agents actually run code inside

# FROM python:3.11-slim
# RUN useradd -m sandboxuser
# USER sandboxuser
# WORKDIR /workspace
