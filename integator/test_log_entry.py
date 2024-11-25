from integator.log_entry import LogEntry


def test_entry_identity():
    input = "123456 2 minutes ago Martin Bernstorff [✅] Testing"

    for _ in range(1, 3):
        entry = LogEntry.from_str(input, 1)
        assert entry.to_str() == input
        input = entry.to_str()
