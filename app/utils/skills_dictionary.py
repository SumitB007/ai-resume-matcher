"""Curated skills dictionary for keyword extraction.

A comprehensive set of tech skills, tools, and frameworks commonly found
in job descriptions. Used for keyword matching and gap analysis.
"""

# ── Programming Languages ──
PROGRAMMING_LANGUAGES = {
    "python", "java", "javascript", "typescript", "c", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
    "lua", "dart", "elixir", "haskell", "clojure", "objective-c", "assembly",
    "bash", "shell", "powershell", "sql", "nosql", "graphql",
}

# ── Frameworks & Libraries ──
FRAMEWORKS = {
    "react", "angular", "vue", "svelte", "next.js", "nuxt.js", "django",
    "flask", "fastapi", "spring", "spring boot", "express", "nest.js",
    "rails", "ruby on rails", "laravel", "asp.net", ".net", "node.js",
    "jquery", "bootstrap", "tailwind", "material ui", "chakra ui",
    "pytorch", "tensorflow", "keras", "scikit-learn", "pandas", "numpy",
    "celery", "sqlalchemy", "pydantic", "alembic",
}

# ── Databases ──
DATABASES = {
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis",
    "elasticsearch", "cassandra", "dynamodb", "firebase", "supabase",
    "neo4j", "couchdb", "mariadb", "oracle", "sql server", "mssql",
    "pgvector", "pinecone", "weaviate", "chromadb", "milvus",
}

# ── Cloud & DevOps ──
CLOUD_DEVOPS = {
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "terraform", "ansible", "jenkins", "github actions", "gitlab ci",
    "circleci", "travis ci", "nginx", "apache", "heroku", "vercel",
    "netlify", "cloudflare", "lambda", "ec2", "s3", "rds", "ecs",
    "fargate", "eks", "gke", "aks", "cloud run", "cloud functions",
}

# ── Data & ML ──
DATA_ML = {
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "data science", "data engineering", "data pipeline",
    "etl", "spark", "hadoop", "airflow", "kafka", "flink", "dbt",
    "snowflake", "bigquery", "redshift", "databricks", "mlflow",
    "embeddings", "transformers", "llm", "gpt", "bert", "rag",
    "vector search", "semantic search", "recommendation system",
}

# ── Tools & Practices ──
TOOLS_PRACTICES = {
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "slack", "rest api", "grpc", "websocket", "microservices",
    "monolith", "serverless", "event-driven", "message queue",
    "rabbitmq", "sqs", "pub/sub", "oauth", "jwt", "saml",
    "ci/cd", "tdd", "bdd", "agile", "scrum", "kanban",
    "unit testing", "integration testing", "e2e testing",
    "pytest", "jest", "mocha", "selenium", "cypress", "playwright",
    "swagger", "openapi", "postman", "insomnia",
}

# ── Soft Skills ──
SOFT_SKILLS = {
    "leadership", "communication", "teamwork", "problem solving",
    "critical thinking", "project management", "mentoring",
    "collaboration", "presentation", "documentation",
    "code review", "architecture", "system design",
}

# ── Combined Dictionary ──
ALL_SKILLS = (
    PROGRAMMING_LANGUAGES
    | FRAMEWORKS
    | DATABASES
    | CLOUD_DEVOPS
    | DATA_ML
    | TOOLS_PRACTICES
    | SOFT_SKILLS
)


def get_all_skills() -> set[str]:
    """Return the complete set of known skills."""
    return ALL_SKILLS.copy()
