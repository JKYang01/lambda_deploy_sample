FROM public.ecr.aws/lambda/python:3.12

# Set environment variables
# Prevents Python from creating .pyc files, for cleaner container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | sudo POETRY_HOME=/opt/poetry python3 && \
    export PATH="/opt/poetry/bin:$PATH" && \
    poetry config virtualenvs.create false

# Add Poetry to the PATH for all subsequent steps
ENV PATH="/opt/poetry/bin:$PATH"

# Set the working directory
WORKDIR ${LAMBDA_TASK_ROOT}

COPY pyproject.toml ${LAMBDA_TASK_ROOT}
COPY poetry.lock ${LAMBDA_TASK_ROOT}
RUN poetry install --only main --no-interaction --no-ansi

COPY pipeline_utils/ ${LAMBDA_TASK_ROOT}/pipeline_utils
COPY database_service/ ${LAMBDA_TASK_ROOT}/database_service
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/
COPY sheet_transfer_and_ocr.py ${LAMBDA_TASK_ROOT}/

CMD ["lambda_function.lambda_handler"]



