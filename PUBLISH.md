# Publish path

The prepared GitHub Actions workflow builds the Linux CUDA image remotely and
publishes it to GitHub Container Registry (GHCR). This avoids installing Docker or
WSL on the clinic workstation.

The contents of `wan22_worker` should be the root of a new GitHub repository so that
`.github/workflows/build.yml` is detected. Run the workflow manually with version
`0.1.0`; the resulting image is:

```text
ghcr.io/GITHUB_USER/ace-wan22-kelpie:0.1.0
```

For the simplest Salad deployment, make the GHCR package public after the first
successful build. The repository and image contain no API keys, R2 credentials,
patient data, prompts, references, or rendered media. If the package remains private,
Salad also needs separate read-only GHCR credentials.
