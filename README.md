# Integator

## Architecture concerns

**Can't we just use an existing DAG tool as the job engine?**
We do not want to use an existing DAG tool as the job-engine, because that makes it very hard to get step status,
and therefore how to present it nicely and log it to persistence.

## Roadmap
* p1: In a monorepo, if you init, it uses the git root. Instead, we want it to uses the current directory.