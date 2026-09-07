# Contributing

Contributions are welcome. Please keep this repository free of real account data.

Before committing:

1. use synthetic IDs and placeholder tokens in examples,
2. never commit packet captures or proxy exports,
3. never log HTTP Authorization headers or raw `/api/user/homepage` payloads,
4. run the tests and privacy audit.

```bash
python -m compileall custom_components tests
pytest -q
./scripts/privacy_audit.sh
```
