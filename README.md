# Integator

## Architecture concerns

**Can't we just use an existing DAG tool as the job engine?**
We do not want to use an existing DAG tool as the job-engine, because that makes it very hard to get step status,
and therefore how to present it nicely and log it to persistence.