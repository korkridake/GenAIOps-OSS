FROM ghcr.io/berriai/litellm:main-latest

# Copy the proxy configuration into the image
COPY config.yaml /app/config.yaml

# Expose the default LiteLLM proxy port
EXPOSE 4000

# Start the proxy using the bundled config
CMD ["--config", "/app/config.yaml", "--host", "0.0.0.0", "--port", "4000"]
