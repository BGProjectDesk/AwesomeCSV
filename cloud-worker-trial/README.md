# Cloud model connection trial (draft)

This isolated branch prepares a small software-adapter test on **standard GitHub-hosted Linux runners**. It does not use a self-hosted runner or the account owner's PC.

## Current state
No external model is connected or verified by this branch yet. No model generations are authorised by the first-stage workflow. The existing catalogue submission lives on a separate branch.

## First-stage contract
- Manual start only, with STOP as the default.
- Run deterministic adapter self-tests in the hosted runner.
- A separate explicit FREE confirmation plus a repository secret named `GROQ_API_KEY` permits exactly one documented model-availability GET.
- No completion POST, automatic retry, redirect, fallback, package installation, scraping, messaging or customer input.
- Logs contain only bounded public model metadata and sanitised status. The key remains in GitHub's encrypted secret store and is never a workflow input, source file, URL parameter, artifact or printed value.
- A catalogue entry does not prove that a model is free for an account, suitable for a task or actually working.

## Owner-controlled connection
The owner signs in or registers with Groq, reviews the account/model terms and confirms a Free account with no payment method or paid billing agreement. The owner creates a key and stores it directly in this repository's **Settings → Secrets and variables → Actions → New repository secret**, named `GROQ_API_KEY`. Never paste it into a chat.

The owner also reviews GitHub Actions' applicable terms and enables the repository's workflows if required. The workflow must exist on the default branch before GitHub exposes its manual start control; publishing this draft branch does not enable or run it.

## Next stage
After the actual availability response is reviewed, select five distinct supported text models and bind approval to an exact manifest and a fixed synthetic workload. A proposed later comparison is capped at ten completion requests: the same five calls in serial and then in parallel. That second stage is not authorised or implemented by the connection-only workflow.

Per-model correctness, errors and total elapsed time must be reported. Root review and correction time is measured before any throughput benefit is claimed. Five models are not five independent providers or independent quota pools. No paid order, demand, revenue or guaranteed capacity is implied.

GitHub Actions is used only to develop and test this adapter. It is not offered as a production hosting service or an always-on commercial worker platform.

## References
- [GitHub Actions billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage)
- [GitHub Actions additional terms](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features#actions)
- [GitHub repository secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [Groq API documentation](https://console.groq.com/docs/quickstart)
