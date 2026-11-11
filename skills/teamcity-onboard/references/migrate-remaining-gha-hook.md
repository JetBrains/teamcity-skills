# Migrate remaining GitHub Actions workflows

This hook now ships as the separate `teamcity-migrate-remaining-gha` skill.
After explicit consent for the migration scope, load its full instructions:

```sh
teamcity skill guide teamcity-migrate-remaining-gha
```

Installation is optional. Before consent, do not load or execute the hook.
If the CLI does not bundle it, report the error and recommend upgrading to a
release that includes it; stop rather than inventing instructions.
