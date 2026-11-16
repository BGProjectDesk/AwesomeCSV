# Cloud worker resources

## Active native cloud-model pool

Five new worker instances have responded using these configured model variants:
- GPT-6.1 Sol
- GPT-6.1 Terra
- GPT-6 Astra
- GPT-6 Sol
- GPT-6 Luna

The owner explicitly requested cloud resources or other AI models. These workers used no local shell, filesystem, browser controller, model installation, PC CPU/GPU inference or external API account. Up to three workers may be active at once.

See [the exact initial results and corrections](native-worker-check.json).
The initial scope score was 29/30; all five returned the exact synthetic Markdown and CSV strings. Three passed the complete initial check. One model returned an unauthorised ACCEPT decision; another omitted the proposed checks from its offer. Their initial failures are preserved, alongside follow-up corrections and restrictions.

This is a small calibration, not proof of paid-task throughput, specialist ability or earnings. All five use the existing shared Codex allowance. They are not five independent providers, independent free quotas or new paid subscriptions. Root retains all scope decisions, account actions, commitments and outgoing messages.

The inputs are invented; no customer CSV data, identifiers or reports are present.

## Verified cloud code execution

[Runtime proof](cloud-runtime-proof.json) confirms eight own-project Python adapter tests passed on GitHub-hosted Ubuntu. The latest verified run executed at 20:56 UTC and its logs were inspected at 22:14 UTC on 16 November. Provider discovery was skipped, and no completion or customer-data processing occurred.

This establishes a cloud test facility for repository-associated software checks. Each buyer task still requires its own complete scope and regression checks. The [unsent Python-fix offer template](../commercial-operations/python-text-fix-offer-template-20261116.json) uses this actual proof.

## Optional external-provider connection — parked

The separate Groq catalogue adapter and GitHub Actions workflow are a draft only. They are not required for the active native pool. No owner key setup is needed for that pool.

The optional workflow has no push or schedule trigger. Discovery is manual, bound to this exact repository and branch, and requires FREE plus DISCOVER_ONLY and an owner-controlled GitHub secret. It permits one catalogue GET, zero completion POSTs, no redirect, retry or paid fallback. It cannot establish model task suitability or free account entitlement.

GitHub Actions test execution is verified in the runtime proof above. No external provider connection is verified. The script must not be run on the owner's PC. A workflow present only on a feature branch may not expose GitHub's manual start control until it is approved onto the default branch.

GitHub Actions is only a possible adapter-development/test facility, not an always-on commercial worker host.

## References
- [GitHub Actions billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage)
- [GitHub Actions additional terms](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features#actions)
- [GitHub repository secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
